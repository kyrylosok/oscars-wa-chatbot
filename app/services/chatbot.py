import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain

from app.config import get_settings
from app.models import ChatResponse
from app.services.pdf_processor import PDFProcessorService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ChatbotService:
    """Main chatbot service that handles conversation flow and generates responses."""
    
    def __init__(self):
        self.settings = get_settings()
        self.pdf_processor = PDFProcessorService()
        self.memory_service = MemoryService()
        
        # Initialize OpenAI chat model
        self.chat_model = ChatOpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Create custom prompt template
        self.prompt_template = self._create_prompt_template()
        
        # Initialize the chain
        self.qa_chain = None
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the chatbot service."""
        try:
            logger.info("Initializing chatbot service...")
            
            # Initialize PDF processor
            pdf_initialized = await self.pdf_processor.initialize_vectorstore()
            if not pdf_initialized:
                logger.error("Failed to initialize PDF processor")
                return False
                
            # Create conversational retrieval chain
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.chat_model,
                retriever=self.pdf_processor.vectorstore.as_retriever(
                    search_kwargs={"k": 5}
                ),
                memory=None,  # We'll manage memory separately
                return_source_documents=True,
                verbose=True
            )
            
            self.is_initialized = True
            logger.info("Chatbot service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing chatbot service: {e}")
            return False
            
    async def process_message(self, user_id: str, message: str) -> ChatResponse:
        """Process a user message and generate a response."""
        try:
            if not self.is_initialized:
                logger.error("Chatbot service not initialized")
                return ChatResponse(
                    response="I'm sorry, but I'm currently not available. Please try again later.",
                    confidence=0.0
                )
                
            logger.info(f"Processing message from user {user_id}: {message[:50]}...")
            
            # Get conversation history
            chat_history = self._get_formatted_chat_history(user_id)
            
            # Get relevant documents
            relevant_docs = await self.pdf_processor.search_documents(message, k=5)
            
            if not relevant_docs:
                logger.warning(f"No relevant documents found for query: {message}")
                response_text = await self._generate_fallback_response(message)
                confidence = 0.3
                sources = []
            else:
                # Generate response using retrieved documents
                response_text, confidence, sources = await self._generate_response_with_context(
                    message, relevant_docs, chat_history
                )
                
            # Add to conversation memory
            self.memory_service.add_message(user_id, message, response_text)
            
            # Clean up expired conversations periodically
            self.memory_service.cleanup_expired_conversations()
            
            response = ChatResponse(
                response=response_text,
                confidence=confidence,
                sources=sources
            )
            
            logger.info(f"Generated response for user {user_id} with confidence: {confidence}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {e}")
            return ChatResponse(
                response="I'm sorry, but I encountered an error while processing your message. Please try again.",
                confidence=0.0
            )
            
    async def _generate_response_with_context(
        self, 
        question: str, 
        documents: List[Document], 
        chat_history: List[Dict[str, str]]
    ) -> tuple[str, float, List[str]]:
        """Generate response using retrieved documents and conversation history."""
        try:
            # Prepare context from documents
            context = "\n\n".join([doc.page_content for doc in documents])
            
            # Format chat history
            history_text = self._format_chat_history(chat_history)
            
            # Create prompt with context
            prompt = self.prompt_template.format(
                context=context,
                chat_history=history_text,
                question=question
            )
            
            # Generate response
            response = await self.chat_model.ainvoke(prompt)
            response_text = response.content.strip()
            
            # Extract sources
            sources = [doc.metadata.get("source", "Unknown") for doc in documents]
            sources = list(set(sources))  # Remove duplicates
            
            # Calculate confidence based on document relevance
            confidence = self._calculate_confidence(documents, question)
            
            return response_text, confidence, sources
            
        except Exception as e:
            logger.error(f"Error generating response with context: {e}")
            return "I'm sorry, I couldn't generate a proper response.", 0.0, []
            
    def _get_formatted_chat_history(self, user_id: str) -> List[Dict[str, str]]:
        """Get formatted chat history for a user."""
        try:
            history = self.memory_service.get_conversation_history(user_id)
            formatted_history = []
            
            for i in range(0, len(history), 2):
                if i + 1 < len(history):
                    formatted_history.append({
                        "human": history[i].get("content", ""),
                        "ai": history[i + 1].get("content", "")
                    })
                    
            return formatted_history[-5:]  # Keep last 5 exchanges
            
        except Exception as e:
            logger.error(f"Error formatting chat history: {e}")
            return []
            
    def _format_chat_history(self, chat_history: List[Dict[str, str]]) -> str:
        """Format chat history for inclusion in prompt."""
        if not chat_history:
            return "No previous conversation."
            
        formatted = []
        for exchange in chat_history:
            formatted.append(f"Human: {exchange.get('human', '')}")
            formatted.append(f"Assistant: {exchange.get('ai', '')}")
            
        return "\n".join(formatted)
        
    def _create_prompt_template(self) -> PromptTemplate:
        template = """You are a helpful multilingual assistant that answers questions based on the provided product documentation in any language.

        Use the following context to answer the user's question. If the answer isn't available in the context, say so clearly and offer to help with something else.

        Product documentation:
        {context}

        Previous conversation:
        {chat_history}

        User's question:
        {question}

        Guidelines:
        1. Always respond in the same language the user used.
        2. Use the provided context as the main source of truth.
        3. Be concise, friendly, and informative.
        4. If the answer is not in the context, say so transparently.
        5. If the user asks about your language abilities (e.g., "Can you speak Chinese?"), confirm that you understand and speak all languages.
        6. Use the chat history to maintain conversation flow.
        7. Do not make up information not found in the documentation.

        Answer:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "chat_history", "question"]
        )
        
    async def _generate_fallback_response(self, message: str) -> str:
        """Generate a fallback response when no relevant documents are found."""
        try:
            # Create a prompt for fallback responses
            fallback_prompt = """You are a helpful multilingual assistant that only answers questions based on the provided product documentation.

            No relevant information was found in the documentation for this question.

            User's question:
            {question}

            Guidelines:
            1. Always respond in the user's language.
            2. Politely explain that you don't have information on this topic in the product documentation.
            3. Do not make up answers or go beyond what's in the documentation.
            4. If the question is a greeting or thank you, reply warmly and offer assistance.
            5. If the user asks about what languages you can speak (e.g., "Do you speak Chinese?"), confirm that you understand and speak all languages.
            6. Invite the user to ask another product-related question.
            7. Keep responses concise, friendly, and on-topic.

            Response:"""
            
            prompt = fallback_prompt.format(question=message)
            
            # Generate response using OpenAI
            response = await self.chat_model.ainvoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating fallback response: {e}")
            # Return a basic fallback if OpenAI fails
            return "I don't have specific information about that in my product knowledge base. Could you please ask about our product features, specifications, or services?"
            
    def _calculate_confidence(self, documents: List[Document], question: str) -> float:
        """Calculate confidence score based on document relevance."""
        try:
            if not documents:
                return 0.0
                
            # Simple confidence calculation based on number of relevant documents
            # In a real implementation, you might use more sophisticated methods
            base_confidence = min(0.8, 0.3 + (len(documents) * 0.1))
            
            # Boost confidence if question keywords appear in documents
            question_words = set(question.lower().split())
            doc_words = set()
            for doc in documents:
                doc_words.update(doc.page_content.lower().split())
                
            keyword_overlap = len(question_words.intersection(doc_words))
            keyword_boost = min(0.2, keyword_overlap * 0.02)
            
            return min(0.95, base_confidence + keyword_boost)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
            
    async def clear_conversation(self, user_id: str) -> bool:
        """Clear conversation history for a user."""
        return self.memory_service.clear_conversation(user_id)
        
    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get conversation summary for a user."""
        return self.memory_service.get_conversation_summary(user_id)
        
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        try:
            pdf_info = await self.pdf_processor.get_document_info()
            active_conversations = self.memory_service.get_active_conversations_count()
            
            return {
                "initialized": self.is_initialized,
                "pdf_processor": pdf_info,
                "active_conversations": active_conversations,
                "model": self.settings.openai_model,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()} 