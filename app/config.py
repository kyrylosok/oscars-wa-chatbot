import os
from typing import Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    
    # Twilio Configuration (Optional for initial testing)
    twilio_account_sid: Optional[str] = Field(default=None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, env="TWILIO_PHONE_NUMBER")
    
    # Application Configuration
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8080, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    stage: str = Field(default="development", env="STAGE")
    
    gcs_bucket_name: Optional[str] = Field(default=None, env="GCS_BUCKET_NAME")

    # PDF Configuration
    pdf_file_path_dev: str = Field(default="data/product.pdf", env="PDF_FILE_PATH")
    pdf_file_path_prod: str = Field(default="tmp/product.pdf", env="LOCAL_PDF_PATH")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Memory Configuration
    max_conversation_history: int = Field(default=20, env="MAX_CONVERSATION_HISTORY")
    conversation_timeout: int = Field(default=1800, env="CONVERSATION_TIMEOUT")
    
    # Vector Store Configuration
    faiss_index_path_dev: str = Field(default="storage/faiss_index", env="FAISS_INDEX_PATH")
    faiss_index_path_prod: str = Field(default="tmp/faiss_index", env="LOCAL_FAISS_PATH")
    embedding_model: str = Field(default="text-embedding-ada-002", env="EMBEDDING_MODEL")
    
    # Ngrok Configuration
    ngrok_auth_token: Optional[str] = Field(default=None, env="NGROK_AUTH_TOKEN")
    
    @property
    def pdf_file_path(self) -> str:
        if self.stage.lower() == "production":
            return self.pdf_file_path_prod
        return self.pdf_file_path_dev
    
    @property
    def faiss_index_path(self) -> str:
        if self.stage.lower() == "production":
            return self.faiss_index_path_prod
        return self.faiss_index_path_dev

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
