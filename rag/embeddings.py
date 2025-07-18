import asyncio
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from decouple import config

class EmbeddingService:
    """Service for creating text embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service with a specific model."""
        self.model_name = model_name
        self.model = None
        self.embedding_dimension = 384  # Default for all-MiniLM-L6-v2
        
    def _load_model(self):
        """Load the embedding model."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
            # Update embedding dimension based on actual model
            test_embedding = self.model.encode("test")
            self.embedding_dimension = len(test_embedding)
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for given text."""
        if not text.strip():
            return [0.0] * self.embedding_dimension
        
        # Load model if not already loaded
        self._load_model()
        
        # Run embedding in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            self.model.encode, 
            text
        )
        
        return embedding.tolist()
    
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts."""
        if not texts:
            return []
        
        # Load model if not already loaded
        self._load_model()
        
        # Run embedding in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.model.encode,
            texts
        )
        
        return [embedding.tolist() for embedding in embeddings]
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        # Handle zero vectors
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1_np, vec2_np) / (norm1 * norm2))


class OpenAIEmbeddingService:
    """Alternative embedding service using OpenAI's text-embedding-ada-002."""
    
    def __init__(self):
        """Initialize the OpenAI embedding service."""
        self.api_key = config('OPENAI_API_KEY', default='')
        self.embedding_dimension = 1536  # OpenAI text-embedding-ada-002 dimension
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI embeddings")
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding using OpenAI API."""
        if not text.strip():
            return [0.0] * self.embedding_dimension
        
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating OpenAI embedding: {e}")
            # Fallback to zero vector
            return [0.0] * self.embedding_dimension
    
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts using OpenAI API."""
        if not texts:
            return []
        
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Error creating OpenAI embeddings batch: {e}")
            # Fallback to zero vectors
            return [[0.0] * self.embedding_dimension for _ in texts]


# Factory function to get the appropriate embedding service
def get_embedding_service(use_openai: bool = False) -> EmbeddingService:
    """Get embedding service based on configuration."""
    if use_openai:
        openai_api_key = config('OPENAI_API_KEY', default='')
        if openai_api_key:
            try:
                return OpenAIEmbeddingService()
            except (ValueError, ImportError) as e:
                print(f"OpenAI embedding service not available: {e}")
                print("Falling back to sentence-transformers")
        else:
            print("OPENAI_API_KEY not provided, using sentence-transformers")
    
    return EmbeddingService()