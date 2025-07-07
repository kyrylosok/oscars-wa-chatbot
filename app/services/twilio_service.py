import logging
from typing import Dict, Any, Optional
from datetime import datetime

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from app.config import get_settings
from app.models import WhatsAppMessage

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for handling Twilio WhatsApp integration."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Only initialize Twilio client if credentials are provided
        if self.settings.twilio_account_sid and self.settings.twilio_auth_token:
            self.client = Client(
                self.settings.twilio_account_sid,
                self.settings.twilio_auth_token
            )
        else:
            self.client = None
            logger.warning("Twilio credentials not provided. WhatsApp functionality will be disabled.")
        
    async def send_message(self, to_number: str, message_body: str) -> Dict[str, Any]:
        """Send a WhatsApp message to a user."""
        if not self.client:
            return {
                "status": "error",
                "error": "Twilio client not initialized. Check your credentials.",
                "timestamp": datetime.now().isoformat()
            }
            
        try:
            logger.info(f"Sending WhatsApp message to {to_number}: {message_body[:50]}...")
            
            # Ensure the number is in WhatsApp format
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
                
            # Send message via Twilio
            message = self.client.messages.create(
                body=message_body,
                from_=self.settings.twilio_phone_number,
                to=to_number
            )
            
            result = {
                "status": "sent",
                "message_sid": message.sid,
                "to": to_number,
                "body": message_body,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Message sent successfully. SID: {message.sid}")
            return result
            
        except TwilioException as e:
            logger.error(f"Twilio error sending message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "error_code": getattr(e, 'code', None),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def send_typing_indicator(self, to_number: str) -> bool:
        """Send a typing indicator to show the bot is processing."""
        try:
            # Note: WhatsApp doesn't directly support typing indicators via API
            # But we can send a brief message and then the actual response
            # This is a placeholder for future implementation
            return True
            
        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
            return False
            
    def parse_incoming_message(self, form_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """Parse incoming WhatsApp message from Twilio webhook."""
        try:
            # Extract message data from Twilio webhook
            message_sid = form_data.get('MessageSid', '')
            from_number = form_data.get('From', '')
            to_number = form_data.get('To', '')
            body = form_data.get('Body', '')
            
            # Basic validation
            if not all([message_sid, from_number, to_number]):
                logger.warning("Incomplete message data received")
                return None
                
            # Clean up phone number format
            if from_number.startswith('whatsapp:'):
                from_number = from_number[9:]  # Remove 'whatsapp:' prefix
                
            message = WhatsAppMessage(
                message_sid=message_sid,
                from_number=from_number,
                to_number=to_number,
                body=body,
                timestamp=datetime.now()
            )
            
            logger.info(f"Parsed incoming message from {from_number}: {body[:50]}...")
            return message
            
        except Exception as e:
            logger.error(f"Error parsing incoming message: {e}")
            return None
            
    def validate_webhook_signature(self, signature: str, url: str, params: Dict[str, Any]) -> bool:
        """Validate incoming webhook signature for security."""
        try:
            from twilio.request_validator import RequestValidator
            
            validator = RequestValidator(self.settings.twilio_auth_token)
            
            # Convert params to the format expected by Twilio
            form_encoded = []
            for key, value in sorted(params.items()):
                form_encoded.append(f"{key}={value}")
            form_encoded_str = "&".join(form_encoded)
            
            return validator.validate(url, form_encoded_str, signature)
            
        except Exception as e:
            logger.error(f"Error validating webhook signature: {e}")
            return False
            
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get the status of a sent message."""
        if not self.client:
            return {"error": "Twilio client not initialized"}
            
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "message_sid": message.sid,
                "status": message.status,
                "direction": message.direction,
                "from": message.from_,
                "to": message.to,
                "body": message.body,
                "date_created": message.date_created.isoformat() if message.date_created else None,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "date_updated": message.date_updated.isoformat() if message.date_updated else None,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error getting message status: {e}")
            return {"error": str(e), "error_code": getattr(e, 'code', None)}
            
        except Exception as e:
            logger.error(f"Unexpected error getting message status: {e}")
            return {"error": str(e)}
            
    async def send_media_message(self, to_number: str, message_body: str, media_url: str) -> Dict[str, Any]:
        """Send a WhatsApp message with media attachment."""
        if not self.client:
            return {
                "status": "error",
                "error": "Twilio client not initialized. Check your credentials.",
                "timestamp": datetime.now().isoformat()
            }
            
        try:
            logger.info(f"Sending WhatsApp media message to {to_number}")
            
            # Ensure the number is in WhatsApp format
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
                
            # Send message with media via Twilio
            message = self.client.messages.create(
                body=message_body,
                from_=self.settings.twilio_phone_number,
                to=to_number,
                media_url=[media_url]
            )
            
            result = {
                "status": "sent",
                "message_sid": message.sid,
                "to": to_number,
                "body": message_body,
                "media_url": media_url,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Media message sent successfully. SID: {message.sid}")
            return result
            
        except TwilioException as e:
            logger.error(f"Twilio error sending media message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "error_code": getattr(e, 'code', None),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Unexpected error sending media message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    def get_account_info(self) -> Dict[str, Any]:
        """Get Twilio account information."""
        if not self.client:
            return {"error": "Twilio client not initialized"}
            
        try:
            account = self.client.api.accounts(self.settings.twilio_account_sid).fetch()
            
            return {
                "account_sid": account.sid,
                "friendly_name": account.friendly_name,
                "status": account.status,
                "type": account.type,
                "date_created": account.date_created.isoformat() if account.date_created else None,
                "date_updated": account.date_updated.isoformat() if account.date_updated else None
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error getting account info: {e}")
            return {"error": str(e), "error_code": getattr(e, 'code', None)}
            
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {e}")
            return {"error": str(e)}
            
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp."""
        # Remove any existing whatsapp: prefix
        if phone_number.startswith('whatsapp:'):
            phone_number = phone_number[9:]
            
        # Add country code if not present
        if not phone_number.startswith('+'):
            # This is a simple implementation - in production, you'd want
            # more sophisticated phone number validation and formatting
            phone_number = f'+{phone_number}'
            
        return f'whatsapp:{phone_number}'
        
    def extract_phone_number(self, whatsapp_number: str) -> str:
        """Extract clean phone number from WhatsApp format."""
        if whatsapp_number.startswith('whatsapp:'):
            return whatsapp_number[9:]
        return whatsapp_number
        
    async def test_connection(self) -> Dict[str, Any]:
        """Test the Twilio connection and configuration."""
        if not self.client:
            return {
                "status": "disabled",
                "message": "Twilio credentials not provided",
                "timestamp": datetime.now().isoformat()
            }
            
        try:
            # Try to fetch account info as a connection test
            account_info = self.get_account_info()
            
            if "error" in account_info:
                return {
                    "status": "failed",
                    "error": account_info["error"],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "success",
                    "account_sid": account_info["account_sid"],
                    "account_status": account_info["status"],
                    "phone_number": self.settings.twilio_phone_number,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error testing Twilio connection: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 