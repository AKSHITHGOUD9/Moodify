#!/bin/bash

# Moodify Deployment Script
# This script helps deploy the Moodify application

set -e  # Exit on any error

echo "🎵 Moodify Deployment Script"
echo "============================="

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "moodify-web" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

echo "✅ All dependencies found"

# Setup backend
echo "\n🐍 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
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

# Setup frontend
echo "\n⚛️  Setting up frontend..."
cd moodify-web

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating frontend .env file..."
    echo "VITE_BACKEND_URL=http://localhost:8000" > .env
fi

# Build for production (optional)
if [ "$1" = "--build" ]; then
    echo "Building for production..."
    npm run build
fi

cd ..

echo "\n✅ Setup complete!"
echo "\n🚀 To start the application:"
echo "\n1. Start the backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo "\n2. In another terminal, start the frontend:"
echo "   cd moodify-web"
echo "   npm run dev"
echo "\n3. Open http://localhost:5173 in your browser"
echo "\n📝 Don't forget to configure your Spotify API credentials in backend/.env"
echo "\n🎵 Happy music discovery!"