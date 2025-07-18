import asyncio
from typing import List, Optional
from decouple import config
from rag.models import RelevantChunk


class LLMService:
    """Service for generating responses using Language Models."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.openai_api_key = config('OPENAI_API_KEY', default='')
        self.client = None
        
        if self.openai_api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.openai_api_key)
            except ImportError:
                print("OpenAI package not available. Install with: pip install openai")
    
    async def generate_response(
        self,
        query: str,
        relevant_chunks: List[RelevantChunk],
        max_tokens: int = 1000
    ) -> str:
        """Generate a response based on the query and relevant context."""
        
        if self.client:
            return await self._generate_with_openai(query, relevant_chunks, max_tokens)
        else:
            return self._generate_fallback_response(query, relevant_chunks)
    
    async def _generate_with_openai(
        self,
        query: str,
        relevant_chunks: List[RelevantChunk],
        max_tokens: int
    ) -> str:
        """Generate response using OpenAI GPT."""
        
        # Prepare context from relevant chunks
        context = self._prepare_context(relevant_chunks)
        
        # Create the prompt
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context. 
Use the context to provide accurate and relevant answers. If the context doesn't contain enough information 
to answer the question, say so clearly. Always cite which document the information comes from when possible."""
        
        user_prompt = f"""Context:
{context}

Question: {query}

Please provide a comprehensive answer based on the context above."""
        
        try:
            # Run OpenAI API call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating response with OpenAI: {e}")
            return self._generate_fallback_response(query, relevant_chunks)
    
    def _generate_fallback_response(
        self,
        query: str,
        relevant_chunks: List[RelevantChunk]
    ) -> str:
        """Generate a simple fallback response when LLM is not available."""
        
        if not relevant_chunks:
            return f"""I couldn't find any relevant information in your documents to answer the question: "{query}". 
Please make sure you have uploaded and processed documents that contain information related to your query."""
        
        # Create a simple extractive response
        response_parts = [
            f"Based on your uploaded documents, here's what I found related to '{query}':\n"
        ]
        
        for i, chunk in enumerate(relevant_chunks[:3], 1):  # Limit to top 3 chunks
            response_parts.append(
                f"\n{i}. From '{chunk.document_name}' (similarity: {chunk.similarity_score:.2f}):"
            )
            response_parts.append(f"   {chunk.chunk_content[:300]}...")
        
        if len(relevant_chunks) > 3:
            response_parts.append(f"\n... and {len(relevant_chunks) - 3} more relevant sections found.")
        
        response_parts.append(
            "\nNote: OpenAI integration is not configured. For more sophisticated responses, "
            "please set up your OPENAI_API_KEY environment variable."
        )
        
        return "\n".join(response_parts)
    
    def _prepare_context(self, relevant_chunks: List[RelevantChunk]) -> str:
        """Prepare context string from relevant chunks."""
        
        if not relevant_chunks:
            return "No relevant context found."
        
        context_parts = []
        
        for chunk in relevant_chunks:
            context_parts.append(
                f"Document: {chunk.document_name} (Relevance: {chunk.similarity_score:.2f})\n"
                f"Content: {chunk.chunk_content}\n"
            )
        
        return "\n---\n".join(context_parts)


class HuggingFaceLLMService:
    """Alternative LLM service using Hugging Face transformers."""
    
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        """Initialize with a Hugging Face model."""
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        
    def _load_model(self):
        """Load the Hugging Face model."""
        if self.model is None:
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
                
                # Add padding token if it doesn't exist
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    
            except ImportError:
                raise ImportError("transformers package is required for Hugging Face models")
    
    async def generate_response(
        self,
        query: str,
        relevant_chunks: List[RelevantChunk],
        max_length: int = 500
    ) -> str:
        """Generate response using Hugging Face model."""
        
        self._load_model()
        
        # Prepare context
        context = self._prepare_context(relevant_chunks)
        
        # Create prompt
        prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        
        try:
            # Tokenize
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=512)
            
            # Generate response in thread pool
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None,
                lambda: self.model.generate(
                    inputs,
                    max_length=max_length,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the generated part (after the prompt)
            generated_text = response[len(prompt):].strip()
            
            return generated_text if generated_text else "I couldn't generate a response based on the provided context."
            
        except Exception as e:
            print(f"Error generating response with Hugging Face: {e}")
            return f"Error generating response: {str(e)}"
    
    def _prepare_context(self, relevant_chunks: List[RelevantChunk]) -> str:
        """Prepare context string from relevant chunks."""
        if not relevant_chunks:
            return "No context available."
        
        # Combine chunks with document names
        context_parts = []
        for chunk in relevant_chunks[:3]:  # Limit context to avoid token limits
            context_parts.append(f"{chunk.document_name}: {chunk.chunk_content[:200]}")
        
        return " | ".join(context_parts)


# Factory function to get the appropriate LLM service
def get_llm_service(service_type: str = "openai") -> LLMService:
    """Get LLM service based on configuration."""
    
    if service_type == "openai":
        return LLMService()
    elif service_type == "huggingface":
        return HuggingFaceLLMService()
    else:
        return LLMService()  # Default to OpenAI/fallback service