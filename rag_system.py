import time
from typing import List, Dict, Any, Optional
from document_processor import DocumentProcessor

class RAGSystem:
    def __init__(self, document_processor: DocumentProcessor, config):
        self.doc_processor = document_processor
        self.config = config
        
    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate response using retrieved context chunks."""
        if not context_chunks:
            return "I couldn't find any relevant information in your documents to answer this question. Please make sure you have uploaded documents that contain relevant information."
        
        # Prepare context from retrieved chunks
        context_text = "\n\n".join([
            f"From {chunk['filename']} ({chunk['file_type']}):\n{chunk['content']}"
            for chunk in context_chunks
        ])
        
        # For now, use a simple template-based response
        # In production, you would use OpenAI API or another LLM
        response = self._generate_template_response(query, context_text, context_chunks)
        
        return response
    
    def _generate_template_response(self, query: str, context: str, chunks: List[Dict[str, Any]]) -> str:
        """Generate a response using a template (fallback when no LLM API is available)."""
        
        # Analyze the query type
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['what', 'define', 'definition', 'explain']):
            response_type = "explanation"
        elif any(word in query_lower for word in ['how', 'process', 'procedure', 'steps']):
            response_type = "process"
        elif any(word in query_lower for word in ['list', 'enumerate', 'show me']):
            response_type = "list"
        elif any(word in query_lower for word in ['when', 'date', 'time']):
            response_type = "temporal"
        else:
            response_type = "general"
        
        # Create response based on type
        if response_type == "explanation":
            response = f"Based on your documents, here's what I found about your question:\n\n"
        elif response_type == "process":
            response = f"Here's the process/procedure I found in your documents:\n\n"
        elif response_type == "list":
            response = f"Here's the information I found in your documents:\n\n"
        elif response_type == "temporal":
            response = f"Regarding timing/dates, I found this information:\n\n"
        else:
            response = f"Based on your question, here's what I found in your documents:\n\n"
        
        # Add the most relevant chunks
        for i, chunk in enumerate(chunks[:3], 1):  # Top 3 chunks
            response += f"{i}. From '{chunk['filename']}':\n"
            response += f"   {chunk['content'][:300]}{'...' if len(chunk['content']) > 300 else ''}\n\n"
        
        # Add source summary
        sources = list(set([chunk['filename'] for chunk in chunks]))
        if len(sources) > 1:
            response += f"\nThis information was found across {len(sources)} documents: {', '.join(sources[:3])}"
            if len(sources) > 3:
                response += f" and {len(sources) - 3} others"
        else:
            response += f"\nSource: {sources[0]}"
        
        return response
    
    def _generate_llm_response(self, query: str, context: str) -> str:
        """Generate response using OpenAI API (when available)."""
        try:
            import openai
            
            if not self.config.OPENAI_API_KEY:
                return self._generate_template_response(query, context, [])
            
            client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
            
            prompt = f"""You are a helpful assistant that answers questions based on provided context from documents.

Context from documents:
{context}

Question: {query}

Please provide a helpful and accurate answer based on the context provided. If the context doesn't contain enough information to answer the question, say so clearly. Always cite which document(s) the information comes from."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on document context."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error with OpenAI API: {e}")
            # Fallback to template response
            return self._generate_template_response(query, context, [])
    
    def process_query(self, query: str, user_id: int) -> Dict[str, Any]:
        """Process a user query and return response with metadata."""
        start_time = time.time()
        
        try:
            # Search for relevant documents
            retrieved_chunks = self.doc_processor.search_documents(
                query=query,
                user_id=user_id,
                limit=self.config.MAX_RETRIEVAL_RESULTS
            )
            
            # Generate response
            if retrieved_chunks:
                # Try LLM first, fallback to template
                if self.config.OPENAI_API_KEY:
                    context_text = "\n\n".join([chunk['content'] for chunk in retrieved_chunks])
                    response = self._generate_llm_response(query, context_text)
                else:
                    response = self.generate_response(query, retrieved_chunks)
            else:
                response = "I couldn't find any relevant information in your documents to answer this question. Please make sure you have uploaded documents that contain relevant information."
            
            processing_time = time.time() - start_time
            
            # Calculate confidence score based on retrieval scores
            confidence_score = 0.0
            if retrieved_chunks:
                scores = [chunk.get('score', 0.0) for chunk in retrieved_chunks]
                confidence_score = sum(scores) / len(scores) if scores else 0.0
            
            return {
                'response': response,
                'retrieved_chunks_count': len(retrieved_chunks),
                'processing_time': processing_time,
                'confidence_score': confidence_score,
                'sources': list(set([chunk['filename'] for chunk in retrieved_chunks])) if retrieved_chunks else []
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                'response': f"An error occurred while processing your query: {str(e)}",
                'retrieved_chunks_count': 0,
                'processing_time': processing_time,
                'confidence_score': 0.0,
                'sources': []
            }
    
    def get_query_suggestions(self, user_id: int) -> List[str]:
        """Get query suggestions based on user's documents."""
        suggestions = [
            "What are the main topics covered in my documents?",
            "Can you summarize the key points from my files?",
            "What important information should I know?",
            "Are there any specific procedures or processes mentioned?",
            "What dates or deadlines are mentioned in the documents?"
        ]
        
        # Could be enhanced to be more specific based on actual document content
        return suggestions