
PDF Query Chatbot

This application is a chatbot that allows querying PDF documents using natural language processing. It utilizes Flask as the web framework and integrates LangChain with Google's AI services for processing and querying PDFs.

Google API Dependency

This application relies on Google's APIs for processing and querying PDFs as follows:

1. Embeddings: The app uses GoogleGenerativeAIEmbeddings from LangChain to create vector representations of the text from PDFs.
2. Language Model: It uses ChatGoogleGenerativeAI, Google's language model accessed through LangChain, for question-answering.
3. API Key: The app requires a Google API key to access these services. Ensure the GOOGLE_API_KEY environment variable is set.

How it Works

1. When a PDF is uploaded, the text is extracted and split into chunks.
2. These chunks are converted into embeddings using Google's embedding model.
3. The embeddings are stored in a FAISS index for efficient retrieval.
4. When a user submits a query, it's processed by the ConversationalRetrievalChain:
   - The query is converted to an embedding.
   - Similar chunks are retrieved from the FAISS index.
   - The retrieved chunks and the query are sent to Google's language model (Gemini 1.5 Pro) to generate a response.

Important Notes

- A valid Google API key with access to these services is required.
- API calls (and potential costs) will be incurred with each query.


Setup

1. Make sure you are in the apps folder.
2. Install the required dependencies using:  
   pip install -r requirements.txt
3. Set up your Google API key as an environment (.env) variable at the root of the project:  
   GOOGLE_API_KEY='your-api-key-here'
4. Run the Flask app:  
   python app.py

Usage

- Upload PDF documents through the web interface.
- Use the chat interface to ask questions about the uploaded documents.
- The app utilizes Google AI services to interpret your queries and generate responses based on the content of the PDFs.