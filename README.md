# WhatsApp Chatbot with PDF Knowledge Base

A sophisticated WhatsApp chatbot that answers questions based on PDF product documentation using LangChain, OpenAI, Twilio, and FAISS vector store.

## 🚀 Features

- **PDF Knowledge Base**: Automatically processes and indexes PDF documents using FAISS
- **WhatsApp Integration**: Seamless integration with Twilio WhatsApp API
- **Conversation Memory**: Maintains context across conversations using LangChain memory buffers
- **RAG (Retrieval-Augmented Generation)**: Combines document retrieval with OpenAI's language models
- **Multi-user Support**: Handles multiple concurrent conversations with isolated memory
- **Real-time Processing**: Asynchronous message processing for optimal performance
- **Comprehensive API**: RESTful API endpoints for testing and administration
- **Development Mode**: Automatic ngrok tunnel setup for easy local development

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WhatsApp      │    │   Twilio API    │    │   FastAPI       │
│   User          │◄──►│   Webhook       │◄──►│   Application   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   OpenAI API    │◄────────────┤
                       │   GPT Models    │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   FAISS Vector  │◄────────────┤
                       │   Store         │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   LangChain     │◄────────────┘
                       │   Memory        │
                       └─────────────────┘
```

## 📋 Prerequisites

- Python 3.8+
- OpenAI API key
- Twilio account with WhatsApp sandbox or approved WhatsApp Business API
- PDF document(s) for the knowledge base

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd chatbot-whatsapp
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment configuration**:
   ```bash
   cp env.example .env
   ```

5. **Configure your environment variables** in `.env`:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-3.5-turbo
   
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=whatsapp:+14155238886
   
   # Application Configuration
   APP_HOST=0.0.0.0
   APP_PORT=8000
   DEBUG=false
   STAGE=development  # development or production
   
   # PDF Configuration
   PDF_FILE_PATH=data/product.pdf
   ```

6. **Add your PDF document**:
   ```bash
   mkdir -p data
   # Copy your PDF file to data/product.pdf
   ```

## 🚀 Usage

### 1. Start the Application

```bash
python -m app.main
```

The application will start on `http://localhost:8000` by default.

### 2. Configure Twilio Webhook

**Development Mode (Automatic):**
- Set `STAGE=development` in your `.env` file
- The application will automatically start an ngrok tunnel
- Copy the webhook URL from the console output
- Go to Twilio Console > WhatsApp > Sandbox and paste the URL

**Production Mode:**
- Set `STAGE=production` in your `.env` file
- Set the webhook URL to: `https://yourdomain.com/webhook/whatsapp`
- No ngrok tunnel will be started

### 3. Test the Chatbot

Send messages to your Twilio WhatsApp number to interact with the chatbot!

## 🔧 API Endpoints

### Core Endpoints

- `GET /` - Application status
- `GET /health` - Health check
- `POST /webhook/whatsapp` - Twilio webhook endpoint

### Chat API

- `POST /api/chat` - Direct chat interface
  ```json
  {
    "user_id": "test_user",
    "message": "What are the product features?"
  }
  ```

- `GET /api/conversation/{user_id}` - Get conversation history
- `DELETE /api/conversation/{user_id}` - Clear conversation

### Administration

- `GET /api/status` - Detailed system status
- `GET /api/document-info` - PDF processing information
- `POST /api/reindex` - Re-index PDF documents

### Development Tools

- `GET /api/ngrok/status` - Ngrok tunnel status
- `GET /api/ngrok/info` - Detailed tunnel information
- `POST /api/ngrok/refresh` - Refresh ngrok tunnel

### Testing

- `POST /api/send-message` - Send WhatsApp message
  ```json
  {
    "to_number": "+1234567890",
    "message_body": "Hello from the bot!"
  }
  ```

## 📁 Project Structure

```
chatbot-whatsapp/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_processor.py # PDF processing & FAISS
│   │   ├── chatbot.py       # Main chatbot logic
│   │   ├── twilio_service.py # WhatsApp integration
│   │   ├── memory_service.py # Conversation memory
│   │   └── ngrok_service.py  # Development tunnel
│   └── utils/
│       ├── __init__.py
│       └── helpers.py       # Utility functions
├── data/
│   └── product.pdf          # Your PDF file
├── storage/
│   └── faiss_index/         # FAISS vector store
├── requirements.txt
├── .env                     # Environment variables
└── README.md
```

## 🎯 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | OpenAI model name | `gpt-3.5-turbo` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Required |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Required |
| `TWILIO_PHONE_NUMBER` | WhatsApp number | Required |
| `APP_HOST` | Application host | `0.0.0.0` |
| `APP_PORT` | Application port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
| `STAGE` | Environment stage | `development` |
| `PDF_FILE_PATH` | Path to PDF file | `data/product.pdf` |
| `CHUNK_SIZE` | Text chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |
| `MAX_CONVERSATION_HISTORY` | Max conversation messages | `20` |
| `CONVERSATION_TIMEOUT` | Session timeout (seconds) | `1800` |

### Customization

The chatbot can be customized by:

1. **Modifying the prompt template** in `app/services/chatbot.py`
2. **Adjusting chunk size and overlap** for better document processing
3. **Changing the OpenAI model** for different response styles
4. **Adding custom preprocessing** for your specific PDF format

## 🔍 Troubleshooting

### Common Issues

1. **"PDF file not found"**
   - Ensure your PDF file is in the `data/` directory
   - Check the `PDF_FILE_PATH` environment variable

2. **"Twilio connection failed"**
   - Verify your Twilio credentials
   - Check if your WhatsApp number is properly formatted

3. **"OpenAI API error"**
   - Verify your OpenAI API key
   - Check if you have sufficient API credits

4. **"FAISS index not loading"**
   - Delete the `storage/faiss_index/` directory and restart
   - The system will recreate the index from your PDF

5. **"Ngrok tunnel failed"**
   - Make sure ngrok is installed: `pip install pyngrok`
   - Check if ngrok is available in your PATH
   - Try refreshing the tunnel: `POST /api/ngrok/refresh`

### Debug Mode

Enable debug mode by setting `DEBUG=true` in your `.env` file.

## 🚀 Deployment

### Using Docker (Recommended)

1. Create a `Dockerfile`:
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["python", "-m", "app.main"]
   ```

2. Build and run:
   ```bash
   docker build -t whatsapp-chatbot .
   docker run -p 8000:8000 --env-file .env whatsapp-chatbot
   ```

### Using Cloud Services

Deploy to platforms like:
- **Heroku**: Add a `Procfile` with `web: python -m app.main`
- **AWS ECS**: Use the Docker image
- **Google Cloud Run**: Deploy containerized app
- **Railway**: Direct deployment from GitHub

## 📊 Performance Optimization

1. **Vector Store**: Use GPU-accelerated FAISS for large documents
2. **Caching**: Implement Redis for conversation caching
3. **Background Processing**: Use Celery for heavy operations
4. **Load Balancing**: Use multiple instances behind a load balancer

## 🔐 Security

- **Webhook Validation**: Twilio signature validation is implemented
- **Input Sanitization**: User inputs are sanitized
- **Rate Limiting**: Implement rate limiting for production use
- **API Keys**: Never commit API keys to version control

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🆘 Support

If you encounter any issues:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Ensure all environment variables are set correctly
4. Test individual components using the API endpoints

## 🛣️ Roadmap

- [ ] Support for multiple PDF documents
- [ ] Advanced conversation analytics
- [ ] Multi-language support
- [ ] Voice message support
- [ ] Integration with other messaging platforms
- [ ] Dashboard for conversation management
- [ ] Automated PDF updates
- [ ] Custom embedding models

---

**Built with ❤️ using FastAPI, LangChain, OpenAI, and Twilio** 