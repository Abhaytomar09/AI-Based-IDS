#!/usr/bin/env python
"""
Quick setup script for AI-powered IDS project
Run this to verify installation and create initial directories
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required, but found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    return True

def create_directories():
    """Create required directories."""
    dirs = [
        'logs',
        'models',
        'data/raw',
        'data/processed',
        'config',
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory created: {dir_path}")

def check_imports():
    """Check if main dependencies are installed."""
    packages = [
        'pandas', 'numpy', 'sklearn', 'xgboost', 
        'torch', 'fastapi', 'streamlit', 'shap'
    ]
    
    missing = []
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    return len(missing) == 0, missing

def setup_env_file():
    """Create .env file from template."""
    if not Path('.env').exists() and Path('.env.example').exists():
        import shutil
        shutil.copy('.env.example', '.env')
        print("✅ Created .env from .env.example")
    elif Path('.env').exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  .env.example not found")

def main():
    print("=" * 50)
    print("AI-Powered IDS - Setup Script")
    print("=" * 50)
    print()
    
    # Check Python
    print("1. Checking Python version...")
    if not check_python_version():
        print("\n❌ Setup failed. Please install Python 3.10 or higher.")
        return False
    print()
    
    # Create directories
    print("2. Creating directories...")
    create_directories()
    print()
    
    # Check imports
    print("3. Checking installed packages...")
    all_ok, missing = check_imports()
    if not all_ok:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
    print()
    
    # Setup env
    print("4. Setting up environment file...")
    setup_env_file()
    print()
    
    print("=" * 50)
    if all_ok:
        print("✅ Setup complete! Ready to start.")
        print("\nNext steps:")
        print("1. python -c \"from src.preprocessing import load_and_preprocess; load_and_preprocess('data/sample_flows.csv', 'data/processed/')\"")
        print("2. python src/api.py")
        print("3. streamlit run src/dashboard.py")
    else:
        print("⚠️  Setup partially complete.")
        print("Please install missing packages and try again.")
    print("=" * 50)
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
