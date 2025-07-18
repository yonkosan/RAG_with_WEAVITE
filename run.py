#!/usr/bin/env python3
"""
Startup script for the RAG Application
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import uvicorn
        import fastapi
        import sqlalchemy
        import psycopg2
        print("✓ Core dependencies found")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """Check environment configuration."""
    env_file = Path(".env")
    if not env_file.exists():
        print("✗ .env file not found")
        print("Please copy .env.example to .env and configure it")
        return False
    
    print("✓ Environment file found")
    return True

def main():
    """Main startup function."""
    print("🚀 Starting RAG Application...")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create uploads directory
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    print("✓ Uploads directory ready")
    
    # Create static directory
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    print("✓ Static directory ready")
    
    print("\n📚 RAG Application")
    print("📍 URL: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("\n" + "="*50)
    
    # Start the application
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"✗ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()