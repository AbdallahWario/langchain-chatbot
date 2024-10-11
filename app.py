from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import ConversationalRetrievalChain
import os
from datetime import datetime, timezone
from sqlalchemy import func,desc

from dotenv import load_dotenv

load_dotenv()



app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['UPLOAD_FOLDER'] = 'pdfs'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'




# Fetch the Google API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

# PDF model
class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200))
    author = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Query log model
class QueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_query= db.Column(db.String(500), nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    source = db.Column(db.String(20), nullable=False)  # 'pdf' or 'google'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize FAISS index and QA chain
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
index = None
qa_chain = None

def initialize_index():
    global index, qa_chain
    if os.path.exists("faiss_index"):
        index = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    else:
        index = FAISS.from_texts(["Initialize"], embeddings)
    
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm,
        index.as_retriever(),
        return_source_documents=True
    )

initialize_index()

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Invalid username or password"})
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})



import os

@app.route('/upload', methods=['POST'])
@login_required
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"})
    if file and file.filename.endswith('.pdf'):
        # Ensure the upload folder exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        try:
            file.save(filename)
        except Exception as e:
            return jsonify({"success": False, "message": f"Error saving file: {str(e)}"})
        
        try:
            # Extract text and update index
            loader = PyPDFLoader(filename)
            pages = loader.load_and_split()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_documents(pages)
            
            global index
            index.add_documents(texts)
            index.save_local("faiss_index")
        except Exception as e:
            return jsonify({"success": False, "message": f"Error processing PDF: {str(e)}"})
        
        # Save PDF metadata
        new_pdf = PDF(filename=file.filename, title=request.form.get('title'), author=request.form.get('author'))
        db.session.add(new_pdf)
        db.session.commit()
        
        return jsonify({"success": True, "message": "File uploaded successfully"})
    return jsonify({"success": False, "message": "Invalid file type"})
@app.route('/query', methods=['POST'])
@login_required
def query():
    user_query = request.json.get('user_query', '')
    if not user_query:
        return jsonify({"success": False, "message": "Query cannot be empty"}), 400
    
    chat_history = request.json.get('chat_history', [])
    
    formatted_chat_history = [(str(h[0]), str(h[1])) for h in chat_history]
    
    result = qa_chain.invoke({"question": user_query, "chat_history": formatted_chat_history})
    response = result['answer']
    source = 'pdf'
    
    # If the response is empty or doesn't answer the question, fall back to Google
    if not response or "I don't have enough information" in response:
        llm = ChatGoogleGenerativeAI(model = "gemini-1.5-pro")
        response = llm(user_query)
        source = 'google'
    
    # Log the query
    log = QueryLog(user_id=current_user.id, user_query=user_query, response=response, source=source)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"response": response, "source": source})
@app.route('/chat_history', methods=['GET'])
@login_required
def get_chat_history():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of messages per page
    
    query_logs = db.session.query(QueryLog).filter(QueryLog.user_id == current_user.id).order_by(desc(QueryLog.timestamp)).paginate(page=page, per_page=per_page, error_out=False)

    chat_history = [
        {
            "user_query": log.user_query,
            "response": log.response,
            "timestamp": log.timestamp.isoformat(),
            "source": log.source
        }
        for log in query_logs.items
    ]
    
    return jsonify({
        "chat_history": chat_history,
        "total_pages": query_logs.pages,
        "current_page": page
    })

@app.route('/reports')
@login_required

def reports():
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"})
    
    # Counting total queries
    total_queries = db.session.query(func.count(QueryLog.id)).scalar()
    
    # Counting queries with 'pdf' as source
    pdf_queries = db.session.query(func.count(QueryLog.id)).filter_by(source='pdf').scalar()
    
    # Counting queries with 'google' as source
    google_queries = db.session.query(func.count(QueryLog.id)).filter_by(source='google').scalar()
    
    return render_template('reports.html', total_queries=total_queries, pdf_queries=pdf_queries, google_queries=google_queries)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password=generate_password_hash('password'), role='admin')
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)