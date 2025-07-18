-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Note: The actual embedding dimensions will be determined by the model used
-- sentence-transformers (default): 384 dimensions
-- OpenAI text-embedding-ada-002: 1536 dimensions
-- The application will handle this automatically

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE ragapp TO raguser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO raguser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO raguser;