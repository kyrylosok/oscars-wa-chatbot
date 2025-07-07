import hashlib
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.cloud import storage

logger = logging.getLogger(__name__)

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(f"Downloaded {source_blob_name} from bucket {bucket_name} to {destination_file_name}.")

def generate_user_id(phone_number: str) -> str:
    """Generate a unique user ID from phone number."""
    # Remove any non-digit characters
    cleaned_number = re.sub(r'\D', '', phone_number)
    
    # Create hash for privacy
    hash_object = hashlib.sha256(cleaned_number.encode())
    return hash_object.hexdigest()[:12]


def clean_phone_number(phone_number: str) -> str:
    """Clean and format phone number."""
    # Remove whatsapp: prefix if present
    if phone_number.startswith('whatsapp:'):
        phone_number = phone_number[9:]
    
    # Remove any non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # Ensure it starts with +
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    
    return cleaned


def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format."""
    cleaned = clean_phone_number(phone_number)
    
    # Basic validation: should be + followed by 10-15 digits
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, cleaned))


def format_response_with_sources(response: str, sources: List[str]) -> str:
    """Format response with source information."""
    if not sources:
        return response
    
    # Add source information to response
    source_text = "\n\n📚 *Sources:*\n"
    for i, source in enumerate(sources, 1):
        source_text += f"{i}. {source}\n"
    
    return response + source_text


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text (simple implementation)."""
    # Convert to lowercase and remove punctuation
    text = re.sub(r'[^\w\s]', '', text.lower())
    
    # Split into words
    words = text.split()
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'can', 'may', 'might', 'must', 'shall', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    # Filter out stop words and short words
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Return unique keywords (preserving order)
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    
    return unique_keywords[:max_keywords]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity based on word overlap."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    
    # Try to truncate at sentence boundary
    truncated = text[:max_length]
    last_sentence = truncated.rfind('.')
    
    if last_sentence > max_length * 0.7:  # Only if we don't lose too much content
        return truncated[:last_sentence + 1]
    
    return truncated + "..."


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display."""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 7:
        return timestamp.strftime("%Y-%m-%d %H:%M")
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent potential issues."""
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Limit length
    sanitized = sanitized[:1000]
    
    # Remove excessive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def parse_environment_bool(value: str) -> bool:
    """Parse boolean values from environment variables."""
    return value.lower() in ('true', '1', 'yes', 'on')


def create_error_response(error_type: str, message: str) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "error": True,
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    required_fields = [
        'openai_api_key',
        'twilio_account_sid',
        'twilio_auth_token',
        'twilio_phone_number'
    ]
    
    for field in required_fields:
        if not config.get(field):
            errors.append(f"Missing required configuration: {field}")
    
    # Validate phone number format
    if config.get('twilio_phone_number'):
        if not config['twilio_phone_number'].startswith('whatsapp:'):
            errors.append("Twilio phone number must start with 'whatsapp:'")
    
    return errors


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into chunks with overlap."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending within the last 200 characters
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + chunk_size - 200:
                end = sentence_end + 1
        
        chunks.append(text[start:end])
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def rate_limit_key(user_id: str, action: str) -> str:
    """Generate rate limit key for user actions."""
    return f"rate_limit:{user_id}:{action}"


def is_business_hours(timezone: str = 'UTC') -> bool:
    """Check if current time is within business hours."""
    now = datetime.now()
    
    # Simple business hours: 9 AM to 6 PM, Monday to Friday
    if now.weekday() >= 5:  # Weekend
        return False
    
    hour = now.hour
    return 9 <= hour <= 18 