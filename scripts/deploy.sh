#!/bin/bash

"""
Moodify Deployment and Setup Script
===================================

This script automates the complete setup and deployment process for the Moodify
application. It handles dependency installation, environment configuration,
and service initialization for both development and production environments.

Features:
- Comprehensive dependency checking
- Automatic virtual environment setup
- Environment file configuration
- Frontend and backend setup
- Production build support
- Cross-platform compatibility

Usage:
    ./scripts/deploy.sh           # Development setup
    ./scripts/deploy.sh --build   # Production build

Author: Moodify Development Team
Version: 1.0.0
"""

set -e  # Exit on any error

echo "🎵 Moodify Deployment Script"
echo "============================="

# =============================================================================
# DIRECTORY VALIDATION
# =============================================================================

# Verify we're in the correct project directory
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "moodify-web" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# =============================================================================
# DEPENDENCY CHECKING
# =============================================================================

# Function to check if a command exists in the system PATH
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "🔍 Checking dependencies..."

# Check for Python 3 (required for backend)
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check for Node.js (required for frontend)
if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

# Check for npm (Node package manager)
if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

echo "✅ All dependencies found"

# =============================================================================
# BACKEND SETUP
# =============================================================================

echo "\n🐍 Setting up backend..."
cd backend

# Create Python virtual environment for dependency isolation
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment variables
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Copying from env.txt..."
    if [ -f "env.txt" ]; then
        cp env.txt .env
        echo "📝 Please edit .env file with your Spotify credentials"
    else
        echo "❌ Error: No env.txt template found"
        exit 1
    fi
fi

cd ..

# =============================================================================
# FRONTEND SETUP
# =============================================================================

echo "\n⚛️  Setting up frontend..."
cd moodify-web

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Configure frontend environment variables
if [ ! -f ".env" ]; then
    echo "Creating frontend .env file..."
    echo "VITE_BACKEND_URL=http://localhost:8000" > .env
fi

# Build for production if requested
if [ "$1" = "--build" ]; then
    echo "Building for production..."
    npm run build
fi

cd ..

# =============================================================================
# SETUP COMPLETION AND INSTRUCTIONS
# =============================================================================

echo "\n✅ Setup complete!"
echo "\n🚀 To start the application:"
echo "\n1. Start the backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --host 127.0.0.1 --port 8000"
echo "\n2. In another terminal, start the frontend:"
echo "   cd moodify-web"
echo "   npm run dev"
echo "\n3. Open http://localhost:5173 in your browser"
echo "\n📝 Don't forget to configure your Spotify API credentials in backend/.env"
echo "\n🎵 Happy music discovery!"