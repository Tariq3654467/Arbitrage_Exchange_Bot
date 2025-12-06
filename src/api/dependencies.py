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
    # TODO: Load from config or environment
    correct_username = "admin"
    correct_password = "admin"  # Change this!
    
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

