import logging
import asyncio
import requests
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from pyngrok import ngrok
except ImportError:
    ngrok = None

from app.config import get_settings

logger = logging.getLogger(__name__)


class NgrokService:
    """Service for managing ngrok tunnels in development mode."""
    
    def __init__(self):
        self.settings = get_settings()
        self.tunnel = None
        self.public_url: Optional[str] = None
        self.is_tunnel_active = False
        
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return self.settings.stage.lower() == "development"
        
    async def start_tunnel(self) -> Optional[str]:
        """Start ngrok tunnel if in development mode."""
        if not self.is_development_mode():
            logger.info("Production mode detected, skipping ngrok tunnel")
            return None
            
        if ngrok is None:
            logger.error("pyngrok not installed. Install it with: pip install pyngrok")
            return None
            
        try:
            logger.info("Starting ngrok tunnel for development...")
            
            # Set auth token if provided
            if self.settings.ngrok_auth_token:
                ngrok.set_auth_token(self.settings.ngrok_auth_token)
                logger.info("Ngrok auth token set successfully")
            else:
                logger.warning("No ngrok auth token provided. Using free tier with limitations.")
            
            # Start ngrok tunnel
            self.tunnel = ngrok.connect(self.settings.app_port)
            self.public_url = self.tunnel.public_url
            self.is_tunnel_active = True
            
            logger.info(f"Ngrok tunnel started successfully!")
            logger.info(f"Public URL: {self.public_url}")
            logger.info(f"Webhook URL: {self.public_url}/webhook/whatsapp")
            
            return self.public_url
            
        except Exception as e:
            logger.error(f"Failed to start ngrok tunnel: {e}")
            return None
            
    async def stop_tunnel(self):
        """Stop ngrok tunnel."""
        if self.tunnel:
            try:
                ngrok.disconnect(self.tunnel.public_url)
                self.tunnel = None
                self.public_url = None
                self.is_tunnel_active = False
                logger.info("Ngrok tunnel stopped")
            except Exception as e:
                logger.error(f"Error stopping ngrok tunnel: {e}")
                
    async def get_tunnel_info(self) -> Dict[str, Any]:
        """Get information about the current tunnel."""
        if not self.is_tunnel_active:
            return {
                "active": False,
                "public_url": None,
                "webhook_url": None,
                "stage": self.settings.stage
            }
            
        return {
            "active": True,
            "public_url": self.public_url,
            "webhook_url": f"{self.public_url}/webhook/whatsapp",
            "stage": self.settings.stage,
            "tunnel_name": self.tunnel.name if self.tunnel else None
        }
        
    async def update_twilio_webhook(self, twilio_service) -> bool:
        """Update Twilio webhook URL with ngrok URL."""
        if not self.is_tunnel_active or not self.public_url:
            logger.warning("No active ngrok tunnel to update webhook")
            return False
            
        try:
            webhook_url = f"{self.public_url}/webhook/whatsapp"
            
            # Note: This is a placeholder for webhook update logic
            # In practice, you'd need to use Twilio's API to update the webhook
            # For now, we'll just log the information
            logger.info(f"Update your Twilio webhook URL to: {webhook_url}")
            logger.info("Go to Twilio Console > WhatsApp > Sandbox and update the webhook URL")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Twilio webhook: {e}")
            return False
            
    def get_ngrok_status(self) -> Dict[str, Any]:
        """Get ngrok service status."""
        try:
            if not self.is_development_mode():
                return {
                    "stage": "production",
                    "ngrok_needed": False,
                    "status": "disabled"
                }
                
            if ngrok is None:
                return {
                    "stage": "development",
                    "ngrok_needed": True,
                    "status": "not_installed",
                    "error": "pyngrok not installed"
                }
                
            return {
                "stage": "development",
                "ngrok_needed": True,
                "status": "available" if self.is_tunnel_active else "inactive",
                "public_url": self.public_url,
                "webhook_url": f"{self.public_url}/webhook/whatsapp" if self.public_url else None
            }
            
        except Exception as e:
            logger.error(f"Error getting ngrok status: {e}")
            return {
                "stage": self.settings.stage,
                "status": "error",
                "error": str(e)
            }
            
    def print_development_info(self):
        """Print development setup information."""
        if not self.is_development_mode():
            return
            
        print("\n" + "="*60)
        print("🚀 DEVELOPMENT MODE SETUP")
        print("="*60)
        
        if self.is_tunnel_active and self.public_url:
            print(f"✅ Ngrok tunnel is active!")
            print(f"   Public URL: {self.public_url}")
            print(f"   Webhook URL: {self.public_url}/webhook/whatsapp")
            print()
            print("📋 Next steps:")
            print("1. Go to Twilio Console > WhatsApp > Sandbox")
            print(f"2. Set webhook URL to: {self.public_url}/webhook/whatsapp")
            print("3. Save the configuration")
            print("4. Test by sending a WhatsApp message!")
        else:
            print("❌ Ngrok tunnel not active")
            print("   Make sure ngrok is installed and accessible")
            
        print("="*60)
        
    async def check_tunnel_health(self) -> bool:
        """Check if the tunnel is healthy and accessible."""
        if not self.is_tunnel_active or not self.public_url:
            return False
            
        try:
            # Test if the tunnel is accessible
            response = requests.get(f"{self.public_url}/health", timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Tunnel health check failed: {e}")
            return False
            
    async def refresh_tunnel(self) -> Optional[str]:
        """Refresh the ngrok tunnel (useful if it disconnects)."""
        if not self.is_development_mode():
            return None
            
        logger.info("Refreshing ngrok tunnel...")
        
        # Stop existing tunnel
        await self.stop_tunnel()
        
        # Start new tunnel
        return await self.start_tunnel()
        
    def get_tunnel_logs(self) -> Dict[str, Any]:
        """Get ngrok tunnel logs and statistics."""
        if not self.is_tunnel_active:
            return {"error": "No active tunnel"}
            
        try:
            # Get ngrok API info
            api_url = "http://localhost:4040/api/tunnels"
            response = requests.get(api_url, timeout=2)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Could not fetch ngrok API data"}
                
        except Exception as e:
            logger.debug(f"Could not fetch ngrok logs: {e}")
            return {"error": str(e)} 