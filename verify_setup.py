#!/usr/bin/env python3
"""
Quick verification script to check if everything is set up correctly
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists"""
    path = Path(filepath)
    if path.exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} missing: {filepath}")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if env_path.exists():
        print("✅ .env file exists")
        return True
    elif example_path.exists():
        print("⚠️  .env file not found, but .env.example exists")
        print("   Please copy .env.example to .env and configure it")
        return False
    else:
        print("❌ Neither .env nor .env.example found")
        return False

def check_docker():
    """Check if Docker is available"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Docker is available: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker is not working properly")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed or not in PATH")
        return False
    except Exception as e:
        print(f"⚠️  Could not check Docker: {e}")
        return False

def check_python_dependencies():
    """Check if required Python packages are available"""
    required = ['yaml', 'fastapi', 'uvicorn', 'pydantic']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ Python package available: {package}")
        except ImportError:
            print(f"❌ Python package missing: {package}")
            missing.append(package)
    
    return len(missing) == 0

def main():
    print("=" * 60)
    print("Arbitrage Bot - Setup Verification")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Check critical files
    print("📁 Checking files...")
    all_ok &= check_file_exists("docker-compose.yml", "Docker Compose file")
    all_ok &= check_file_exists("Dockerfile", "Backend Dockerfile")
    all_ok &= check_file_exists("frontend/Dockerfile", "Frontend Dockerfile")
    all_ok &= check_file_exists("config/config.yaml", "Configuration file")
    all_ok &= check_file_exists("requirements.txt", "Python requirements")
    all_ok &= check_file_exists("frontend/package.json", "Frontend package.json")
    all_ok &= check_file_exists("src/api/main.py", "API main file")
    all_ok &= check_file_exists("run_dashboard.py", "Dashboard runner")
    print()
    
    # Check environment
    print("🔐 Checking environment...")
    all_ok &= check_env_file()
    print()
    
    # Check Docker
    print("🐳 Checking Docker...")
    docker_ok = check_docker()
    print()
    
    # Check Python dependencies
    print("🐍 Checking Python dependencies...")
    deps_ok = check_python_dependencies()
    print()
    
    # Summary
    print("=" * 60)
    if all_ok and docker_ok and deps_ok:
        print("✅ All checks passed! You're ready to start the bot.")
        print()
        print("Next steps:")
        print("1. Copy .env.example to .env and configure it")
        print("2. Run: docker-compose up -d --build")
        print("3. Access dashboard at http://localhost:3001")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

