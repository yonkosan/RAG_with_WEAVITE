import os
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any
import weaviate
from weaviate.classes.config import Configure
from sentence_transformers import SentenceTransformer

# Document parsing imports
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document as DocxDocument
import PyPDF2

class DocumentProcessor:
    def __init__(self, weaviate_client, config):
        self.client = weaviate_client
        self.config = config
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def parse_document(self, file_path: str, file_type: str) -> str:
        """Parse document based on file type and return text content."""
        try:
            if file_type.lower() == 'pdf':
                return self._parse_pdf(file_path)
            elif file_type.lower() == 'docx':
                return self._parse_docx(file_path)
            elif file_type.lower() == 'txt':
                return self._parse_txt(file_path)
            elif file_type.lower() == 'json':
                return self._parse_json(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error parsing {file_type} file: {str(e)}")
    
    def _parse_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            # Try with pdfminer first
            text = extract_pdf_text(file_path)
            if text.strip():
                return text
        except:
            pass
        
        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise Exception(f"Failed to parse PDF: {str(e)}")
    
    def _parse_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        doc = DocxDocument(file_path)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        return '\n'.join(text)
    
    def _parse_txt(self, file_path: str) -> str:
        """Read text file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    
    def _parse_json(self, file_path: str) -> str:
        """Parse JSON file and convert to text."""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return json.dumps(data, indent=2)
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into chunks for embedding."""
        chunk_size = chunk_size or self.config.CHUNK_SIZE
        overlap = overlap or self.config.CHUNK_OVERLAP
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                for i in range(end, max(start + chunk_size//2, end - 100), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
            if start >= len(text):
                break
        
        return chunks
    
    def create_or_get_collection(self, user_id: int) -> str:
        """Create or get a Weaviate collection for the user."""
        collection_name = f"UserDocuments_{user_id}"
        
        try:
            # Check if collection exists
            if self.client.collections.exists(collection_name):
                return collection_name
            
            # Create new collection
            collection = self.client.collections.create(
                name=collection_name,
                vectorizer_config=Configure.Vectorizer.none(),  # We'll add vectors manually
                properties=[
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "The text content of the document chunk"
                    },
                    {
                        "name": "document_id",
                        "dataType": ["int"],
                        "description": "Reference to the document ID"
                    },
                    {
                        "name": "chunk_index",
                        "dataType": ["int"],
                        "description": "Index of the chunk within the document"
                    },
                    {
                        "name": "filename",
                        "dataType": ["text"],
                        "description": "Original filename"
                    },
                    {
                        "name": "file_type",
                        "dataType": ["text"],
                        "description": "Type of the source file"
                    }
                ]
            )
            
            return collection_name
            
        except Exception as e:
            raise Exception(f"Error creating collection: {str(e)}")
    
    def process_and_store_document(self, file_path: str, document_record: Any) -> int:
        """Process document and store chunks in Weaviate."""
        try:
            # Parse document
            content = self.parse_document(file_path, document_record.file_type)
            
            # Create chunks
            chunks = self.chunk_text(content)
            
            if not chunks:
                raise Exception("No content extracted from document")
            
            # Get or create collection
            collection_name = self.create_or_get_collection(document_record.user_id)
            collection = self.client.collections.get(collection_name)
            
            # Generate embeddings and store chunks
            stored_count = 0
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Skip empty chunks
                    # Generate embedding
                    embedding = self.embedding_model.encode(chunk).tolist()
                    
                    # Store in Weaviate
                    collection.data.insert(
                        properties={
                            "content": chunk,
                            "document_id": document_record.id,
                            "chunk_index": i,
                            "filename": document_record.original_filename,
                            "file_type": document_record.file_type
                        },
                        vector=embedding
                    )
                    stored_count += 1
            
            # Update document record
            document_record.processed = True
            document_record.weaviate_class_name = collection_name
            document_record.chunk_count = stored_count
            document_record.content_preview = content[:500] + "..." if len(content) > 500 else content
            
            return stored_count
            
        except Exception as e:
            raise Exception(f"Error processing document: {str(e)}")
    
    def search_documents(self, query: str, user_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Search for relevant document chunks based on query."""
        limit = limit or self.config.MAX_RETRIEVAL_RESULTS
        
        try:
            collection_name = f"UserDocuments_{user_id}"
            
            if not self.client.collections.exists(collection_name):
                return []
            
            collection = self.client.collections.get(collection_name)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search similar chunks
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                return_metadata=['score']
            )
            
            results = []
            for obj in response.objects:
                results.append({
                    'content': obj.properties['content'],
                    'filename': obj.properties['filename'],
                    'file_type': obj.properties['file_type'],
                    'document_id': obj.properties['document_id'],
                    'chunk_index': obj.properties['chunk_index'],
                    'score': obj.metadata.score if obj.metadata.score else 0.0
                })
            
            return results
            
        except Exception as e:
            raise Exception(f"Error searching documents: {str(e)}")
    
    def delete_user_documents(self, user_id: int):
        """Delete all documents for a user from Weaviate."""
        try:
            collection_name = f"UserDocuments_{user_id}"
            if self.client.collections.exists(collection_name):
                self.client.collections.delete(collection_name)
        except Exception as e:
            print(f"Error deleting user documents: {str(e)}")
    
    def delete_document_chunks(self, document_id: int, user_id: int):
        """Delete specific document chunks from Weaviate."""
        try:
            collection_name = f"UserDocuments_{user_id}"
            if self.client.collections.exists(collection_name):
                collection = self.client.collections.get(collection_name)
                
                # Delete chunks for specific document
                collection.data.delete_many(
                    where={
                        "path": ["document_id"],
                        "operator": "Equal",
                        "valueInt": document_id
                    }
                )
        except Exception as e:
            print(f"Error deleting document chunks: {str(e)}")