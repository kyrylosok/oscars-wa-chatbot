from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class WhatsAppMessage(BaseModel):
    """WhatsApp message model."""
    message_sid: str
    from_number: str
    to_number: str
    body: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    confidence: Optional[float] = None
    sources: Optional[List[str]] = None
    
    
class ConversationState(BaseModel):
    """Conversation state model."""
    user_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    last_activity: datetime = Field(default_factory=datetime.now)
    session_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PDFDocument(BaseModel):
    """PDF document model."""
    filename: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentChunk(BaseModel):
    """Document chunk model for vector storage."""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_id: str
    embedding: Optional[List[float]] = None 