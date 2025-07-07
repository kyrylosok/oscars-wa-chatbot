import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.config import get_settings
from app.models import ConversationState

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing conversation memory and chat history."""
    
    def __init__(self):
        self.settings = get_settings()
        self.conversations: Dict[str, ConversationBufferMemory] = {}
        self.conversation_states: Dict[str, ConversationState] = {}
        
    def get_or_create_memory(self, user_id: str) -> ConversationBufferMemory:
        """Get or create conversation memory for a user."""
        try:
            # Check if memory exists and is not expired
            if user_id in self.conversations:
                if self._is_conversation_active(user_id):
                    return self.conversations[user_id]
                else:
                    # Clean up expired conversation
                    self._cleanup_conversation(user_id)
            
            # Create new memory
            memory = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history",
                max_token_limit=self.settings.max_conversation_history * 100  # Rough estimate
            )
            
            self.conversations[user_id] = memory
            self.conversation_states[user_id] = ConversationState(
                user_id=user_id,
                messages=[],
                last_activity=datetime.now()
            )
            
            logger.info(f"Created new conversation memory for user: {user_id}")
            return memory
            
        except Exception as e:
            logger.error(f"Error getting/creating memory for user {user_id}: {e}")
            # Return a fresh memory as fallback
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
            
    def add_message(self, user_id: str, human_message: str, ai_response: str) -> bool:
        """Add a message exchange to the conversation memory."""
        try:
            memory = self.get_or_create_memory(user_id)
            
            # Add messages to memory
            memory.chat_memory.add_user_message(human_message)
            memory.chat_memory.add_ai_message(ai_response)
            
            # Update conversation state
            if user_id in self.conversation_states:
                state = self.conversation_states[user_id]
                state.messages.append({
                    "type": "human",
                    "content": human_message,
                    "timestamp": datetime.now().isoformat()
                })
                state.messages.append({
                    "type": "ai",
                    "content": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
                state.last_activity = datetime.now()
                
                # Keep only recent messages
                if len(state.messages) > self.settings.max_conversation_history * 2:
                    state.messages = state.messages[-self.settings.max_conversation_history * 2:]
                    
            logger.info(f"Added message exchange for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message for user {user_id}: {e}")
            return False
            
    def get_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        try:
            if user_id not in self.conversation_states:
                return []
                
            state = self.conversation_states[user_id]
            return state.messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history for user {user_id}: {e}")
            return []
            
    def get_memory_context(self, user_id: str) -> str:
        """Get formatted memory context for the conversation."""
        try:
            memory = self.get_or_create_memory(user_id)
            
            # Get the conversation buffer
            buffer = memory.buffer
            
            if not buffer:
                return ""
                
            return buffer
            
        except Exception as e:
            logger.error(f"Error getting memory context for user {user_id}: {e}")
            return ""
            
    def clear_conversation(self, user_id: str) -> bool:
        """Clear conversation memory for a user."""
        try:
            if user_id in self.conversations:
                self.conversations[user_id].clear()
                
            if user_id in self.conversation_states:
                self.conversation_states[user_id].messages = []
                self.conversation_states[user_id].last_activity = datetime.now()
                
            logger.info(f"Cleared conversation for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing conversation for user {user_id}: {e}")
            return False
            
    def _is_conversation_active(self, user_id: str) -> bool:
        """Check if a conversation is still active (not expired)."""
        try:
            if user_id not in self.conversation_states:
                return False
                
            state = self.conversation_states[user_id]
            time_diff = datetime.now() - state.last_activity
            
            return time_diff.total_seconds() < self.settings.conversation_timeout
            
        except Exception as e:
            logger.error(f"Error checking conversation activity for user {user_id}: {e}")
            return False
            
    def _cleanup_conversation(self, user_id: str):
        """Clean up expired conversation data."""
        try:
            if user_id in self.conversations:
                del self.conversations[user_id]
                
            if user_id in self.conversation_states:
                del self.conversation_states[user_id]
                
            logger.info(f"Cleaned up expired conversation for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up conversation for user {user_id}: {e}")
            
    def cleanup_expired_conversations(self):
        """Clean up all expired conversations."""
        try:
            expired_users = []
            
            for user_id in list(self.conversation_states.keys()):
                if not self._is_conversation_active(user_id):
                    expired_users.append(user_id)
                    
            for user_id in expired_users:
                self._cleanup_conversation(user_id)
                
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired conversations")
                
        except Exception as e:
            logger.error(f"Error during conversation cleanup: {e}")
            
    def get_active_conversations_count(self) -> int:
        """Get the number of active conversations."""
        try:
            active_count = 0
            for user_id in self.conversation_states:
                if self._is_conversation_active(user_id):
                    active_count += 1
                    
            return active_count
            
        except Exception as e:
            logger.error(f"Error getting active conversations count: {e}")
            return 0
            
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation for a user."""
        try:
            if user_id not in self.conversation_states:
                return {"status": "not_found", "message_count": 0}
                
            state = self.conversation_states[user_id]
            memory = self.conversations.get(user_id)
            
            summary = {
                "user_id": user_id,
                "message_count": len(state.messages),
                "last_activity": state.last_activity.isoformat(),
                "is_active": self._is_conversation_active(user_id),
                "memory_buffer_length": len(memory.buffer) if memory else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting conversation summary for user {user_id}: {e}")
            return {"status": "error", "error": str(e)} 