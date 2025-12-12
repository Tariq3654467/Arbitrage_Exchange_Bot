"""
API Dependencies
Shared dependencies for API routes to avoid circular imports
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional

# Basic authentication
security = HTTPBasic()

# Database instance (set by main.py during startup)
postgres_db: Optional[object] = None


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication"""
    import os
    
    # Load from environment variables with fallback to defaults
    correct_username = os.getenv("API_USERNAME", "admin")
    correct_password = os.getenv("API_PASSWORD", "admin")
    
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

