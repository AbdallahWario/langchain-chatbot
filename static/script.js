document.addEventListener('DOMContentLoaded', (event) => {
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const uploadForm = document.getElementById('upload-form');
    const loginForm = document.getElementById('login-form');
    let currentPage = 1;
    let chatHistory = [];

    if (chatForm) {
        loadChatHistory();

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userInput = document.getElementById('user-input');
            const user_query = userInput.value.trim();
            if (user_query) {  
                appendMessage('You: ' + user_query);
                userInput.value = '';
                try {
                    const response = await fetch('/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ user_query: user_query, chat_history: chatHistory }),
                    });
                    const data = await response.json();
                    appendMessage('Bot: ' + data.response);
                    chatHistory.push([user_query, data.response]);
                } catch (error) {
                    console.error('Error:', error);
                    appendMessage('Bot: Sorry, there was an error processing your request.');
                }
            } else {
                appendMessage('Bot: Please enter a valid query.');  
            }
        });
        
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData,
                });
                const data = await response.json();
                if (data.success) {
                    alert('File uploaded successfully!');
                    uploadForm.reset();
                } else {
                    alert('Error uploading file: ' + data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while uploading the file.');
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(loginForm);
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    body: formData,
                });
                const data = await response.json();
                if (data.success) {
                    // Redirects to home page on successful login
                    window.location.href = '/';  
                } else {
                    alert('Login failed: ' + data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred during login.');
            }
        });
    }

    function appendMessage(message) {
        const messageElement = document.createElement('p');
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function loadChatHistory() {
        try {
            const response = await fetch(`/chat_history?page=${currentPage}`);
            const data = await response.json();
            chatMessages.innerHTML = '';
            data.chat_history.reverse().forEach(message => {
                appendMessage(`You: ${message.user_query}`);
                appendMessage(`Bot: ${message.response}`);
            });
            updatePaginationControls(data.current_page, data.total_pages);
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    function updatePaginationControls(currentPage, totalPages) {
        const paginationContainer = document.getElementById('pagination-container');
        paginationContainer.innerHTML = '';

        if (currentPage > 1) {
            const prevButton = createPaginationButton('Previous', currentPage - 1);
            paginationContainer.appendChild(prevButton);
        }

        for (let i = 1; i <= totalPages; i++) {
            const pageButton = createPaginationButton(i.toString(), i);
            if (i === currentPage) {
                pageButton.classList.add('current-page');
            }
            paginationContainer.appendChild(pageButton);
        }

        if (currentPage < totalPages) {
            const nextButton = createPaginationButton('Next', currentPage + 1);
            paginationContainer.appendChild(nextButton);
        }
    }

    function createPaginationButton(text, page) {
        const button = document.createElement('button');
        button.textContent = text;
        button.addEventListener('click', () => {
            currentPage = page;
            loadChatHistory();
        });
        return button;
    }
});