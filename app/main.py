import logging
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import get_settings
from app.services.chatbot import ChatbotService
from app.services.twilio_service import TwilioService
from app.services.ngrok_service import NgrokService
from app.models import WhatsAppMessage, ChatResponse
from app.utils.helpers import download_blob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
chatbot_service = None
twilio_service = None
ngrok_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting WhatsApp Chatbot application...")
    
    global chatbot_service, twilio_service, ngrok_service
    
    # download files
    if settings.stage == "production":
        await download_blob(settings.gcs_bucket_name, settings.pdf_file_path_dev, settings.pdf_file_path_prod)

    # Initialize services
    chatbot_service = ChatbotService()
    twilio_service = TwilioService()
    ngrok_service = NgrokService()
    
    # Initialize chatbot
    initialized = await chatbot_service.initialize()
    if not initialized:
        logger.error("Failed to initialize chatbot service")
        raise RuntimeError("Chatbot initialization failed")
    
    # Test Twilio connection
    connection_test = await twilio_service.test_connection()
    if connection_test["status"] == "failed":
        logger.warning(f"Twilio connection test failed: {connection_test['error']}")
    else:
        logger.info("Twilio connection test passed")
    
    # Start ngrok tunnel if in development mode
    if ngrok_service.is_development_mode():
        tunnel_url = await ngrok_service.start_tunnel()
        if tunnel_url:
            # Print development setup information
            ngrok_service.print_development_info()
        else:
            logger.warning("Failed to start ngrok tunnel in development mode")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WhatsApp Chatbot application...")
    
    # Stop ngrok tunnel if active
    if ngrok_service and ngrok_service.is_tunnel_active:
        await ngrok_service.stop_tunnel()


# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp Chatbot",
    description="A WhatsApp chatbot that answers questions based on PDF product documentation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load settings
settings = get_settings()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "WhatsApp Chatbot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        status = await chatbot_service.get_system_status()
        return {
            "status": "healthy",
            "timestamp": status["timestamp"],
            "chatbot_initialized": status["initialized"],
            "active_conversations": status["active_conversations"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    MessageSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...)
):
    """Handle incoming WhatsApp messages from Twilio."""
    try:
        # Get form data
        form_data = {
            "MessageSid": MessageSid,
            "From": From,
            "To": To,
            "Body": Body
        }
        
        # Parse incoming message
        message = twilio_service.parse_incoming_message(form_data)
        if not message:
            logger.error("Failed to parse incoming message")
            return PlainTextResponse("Invalid message format", status_code=400)
        
        # Process message in background
        background_tasks.add_task(process_whatsapp_message, message)
        
        # Return empty response (required by Twilio)
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error(f"Error handling WhatsApp webhook: {e}")
        return PlainTextResponse("Internal server error", status_code=500)


async def process_whatsapp_message(message: WhatsAppMessage):
    """Process incoming WhatsApp message and send response."""
    try:
        logger.info(f"Processing WhatsApp message from {message.from_number}")
        
        # Generate response using chatbot
        response = await chatbot_service.process_message(
            user_id=message.from_number,
            message=message.body
        )
        
        # Send response via WhatsApp
        send_result = await twilio_service.send_message(
            to_number=message.from_number,
            message_body=response.response
        )
        
        if send_result["status"] == "error":
            logger.error(f"Failed to send response: {send_result['error']}")
        else:
            logger.info(f"Response sent successfully to {message.from_number}")
            
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        
        # Send error message to user
        try:
            await twilio_service.send_message(
                to_number=message.from_number,
                message_body="I'm sorry, I encountered an error. Please try again later."
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")


@app.post("/api/send-message")
async def send_message(request: Request):
    """Send a message via WhatsApp (for testing)."""
    try:
        data = await request.json()
        to_number = data.get("to_number")
        message_body = data.get("message_body")
        
        if not to_number or not message_body:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: to_number, message_body"
            )
        
        result = await twilio_service.send_message(to_number, message_body)
        return result
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: Request):
    """Chat endpoint for testing chatbot responses."""
    try:
        data = await request.json()
        user_id = data.get("user_id", "test_user")
        message = data.get("message")
        
        if not message:
            raise HTTPException(status_code=400, detail="Missing message")
        
        response = await chatbot_service.process_message(user_id, message)
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversation/{user_id}")
async def get_conversation(user_id: str):
    """Get conversation history for a user."""
    try:
        summary = await chatbot_service.get_conversation_summary(user_id)
        return summary
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversation/{user_id}")
async def clear_conversation(user_id: str):
    """Clear conversation history for a user."""
    try:
        success = await chatbot_service.clear_conversation(user_id)
        return {"success": success, "user_id": user_id}
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_system_status():
    """Get detailed system status."""
    try:
        status = await chatbot_service.get_system_status()
        twilio_status = await twilio_service.test_connection()
        ngrok_status = ngrok_service.get_ngrok_status()
        
        return {
            "chatbot": status,
            "twilio": twilio_status,
            "ngrok": ngrok_status
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ngrok/status")
async def get_ngrok_status():
    """Get ngrok tunnel status."""
    try:
        return ngrok_service.get_ngrok_status()
        
    except Exception as e:
        logger.error(f"Error getting ngrok status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ngrok/info")
async def get_ngrok_info():
    """Get detailed ngrok tunnel information."""
    try:
        tunnel_info = await ngrok_service.get_tunnel_info()
        return tunnel_info
        
    except Exception as e:
        logger.error(f"Error getting ngrok info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ngrok/refresh")
async def refresh_ngrok_tunnel():
    """Refresh ngrok tunnel (development mode only)."""
    try:
        if not ngrok_service.is_development_mode():
            raise HTTPException(
                status_code=400,
                detail="Ngrok tunnel refresh only available in development mode"
            )
        
        new_url = await ngrok_service.refresh_tunnel()
        return {
            "success": new_url is not None,
            "new_url": new_url,
            "webhook_url": f"{new_url}/webhook/whatsapp" if new_url else None
        }
        
    except Exception as e:
        logger.error(f"Error refreshing ngrok tunnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/document-info")
async def get_document_info():
    """Get information about the processed PDF document."""
    try:
        info = await chatbot_service.pdf_processor.get_document_info()
        return info
        
    except Exception as e:
        logger.error(f"Error getting document info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reindex")
async def reindex_documents():
    """Reindex PDF documents (admin endpoint)."""
    try:
        success = await chatbot_service.pdf_processor.reindex_documents()
        return {"success": success, "message": "Reindexing completed"}
        
    except Exception as e:
        logger.error(f"Error reindexing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info"
    ) 