import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import get_settings
from app.models import PDFDocument, DocumentChunk

logger = logging.getLogger(__name__)


class PDFProcessorService:
    """Service for processing PDF documents and managing vector store."""
    
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            api_key=self.settings.openai_api_key,
            model=self.settings.embedding_model
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.vectorstore: Optional[FAISS] = None
        
    async def initialize_vectorstore(self) -> bool:
        """Initialize or load existing vector store."""
        try:
            # Check if FAISS index exists
            if os.path.exists(self.settings.faiss_index_path):
                logger.info("Loading existing FAISS index...")
                self.vectorstore = FAISS.load_local(
                    self.settings.faiss_index_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS index loaded successfully")
                return True
            else:
                logger.info("No existing FAISS index found. Will create new one.")
                return await self.process_pdf_and_create_index()
                
        except Exception as e:
            logger.error(f"Error initializing vectorstore: {e}")
            return False
            
    async def process_pdf_and_create_index(self) -> bool:
        """Process PDF file and create FAISS index."""
        try:
            # Check if PDF file exists
            if not os.path.exists(self.settings.pdf_file_path):
                logger.error(f"PDF file not found at {self.settings.pdf_file_path}")
                return False
                
            logger.info(f"Processing PDF: {self.settings.pdf_file_path}")
            
            # Load PDF document
            loader = PyPDFLoader(self.settings.pdf_file_path)
            documents = loader.load()
            
            logger.info(f"Loaded {len(documents)} pages from PDF")
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split into {len(chunks)} chunks")
            
            # Create FAISS index
            self.vectorstore = FAISS.from_documents(
                chunks,
                self.embeddings
            )
            
            # Save the index
            os.makedirs(os.path.dirname(self.settings.faiss_index_path), exist_ok=True)
            self.vectorstore.save_local(self.settings.faiss_index_path)
            
            logger.info("FAISS index created and saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return False
            
    async def search_documents(self, query: str, k: int = 5) -> List[Document]:
        """Search for relevant documents based on query."""
        try:
            if not self.vectorstore:
                logger.error("Vector store not initialized")
                return []
                
            # Perform similarity search
            docs = self.vectorstore.similarity_search(query, k=k)
            logger.info(f"Found {len(docs)} relevant documents for query: {query[:50]}...")
            
            return docs
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
            
    async def search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """Search for relevant documents with similarity scores."""
        try:
            if not self.vectorstore:
                logger.error("Vector store not initialized")
                return []
                
            # Perform similarity search with scores
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=k)
            logger.info(f"Found {len(docs_with_scores)} relevant documents with scores")
            
            return docs_with_scores
            
        except Exception as e:
            logger.error(f"Error searching documents with scores: {e}")
            return []
            
    async def add_document(self, document: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a new document to the vector store."""
        try:
            if not self.vectorstore:
                logger.error("Vector store not initialized")
                return False
                
            # Create document object
            doc = Document(
                page_content=document,
                metadata=metadata or {}
            )
            
            # Add to vector store
            self.vectorstore.add_documents([doc])
            
            # Save updated index
            self.vectorstore.save_local(self.settings.faiss_index_path)
            
            logger.info("Document added to vector store successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False
            
    async def get_document_info(self) -> Dict[str, Any]:
        """Get information about the processed document."""
        try:
            if not self.vectorstore:
                return {"status": "not_initialized", "document_count": 0}
                
            # Get document count (approximate)
            index_info = {
                "status": "ready",
                "index_path": self.settings.faiss_index_path,
                "pdf_path": self.settings.pdf_file_path,
                "chunk_size": self.settings.chunk_size,
                "chunk_overlap": self.settings.chunk_overlap,
                "embedding_model": self.settings.embedding_model
            }
            
            return index_info
            
        except Exception as e:
            logger.error(f"Error getting document info: {e}")
            return {"status": "error", "error": str(e)}
            
    async def reindex_documents(self) -> bool:
        """Reindex all documents (useful for updates)."""
        try:
            logger.info("Starting document reindexing...")
            
            # Remove existing index
            if os.path.exists(self.settings.faiss_index_path):
                import shutil
                shutil.rmtree(self.settings.faiss_index_path)
                
            # Recreate index
            return await self.process_pdf_and_create_index()
            
        except Exception as e:
            logger.error(f"Error reindexing documents: {e}")
            return False 