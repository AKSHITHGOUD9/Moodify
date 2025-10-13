#!/bin/bash

"""
Moodify Development Startup Script
=================================

This script starts both the backend and frontend services in development mode
with hot reloading enabled. It includes comprehensive error checking, dependency
validation, and graceful shutdown handling.

Features:
- Automatic dependency checking and installation
- Background process management
- Health check integration
- Graceful shutdown on interruption
- Cross-platform compatibility

Usage:
    ./scripts/dev.sh

Author: Moodify Development Team
Version: 1.0.0
"""

set -e  # Exit on any error

echo "🎵 Starting Moodify in Development Mode"
echo "====================================="

# =============================================================================
# DIRECTORY VALIDATION
# =============================================================================

# Verify we're in the correct project directory
if [ ! -f "README.md" ] || [ ! -d "backend-openai" ] || [ ! -d "moodify-web" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# =============================================================================
# CLEANUP AND SIGNAL HANDLING
# =============================================================================

# Function to gracefully shutdown all background processes
cleanup() {
    echo "\n🛑 Shutting down services..."
    jobs -p | xargs -r kill
    exit 0
}

# Set trap to cleanup on script exit or interruption
trap cleanup SIGINT SIGTERM

# =============================================================================
# ENVIRONMENT CONFIGURATION VALIDATION
# =============================================================================

# Check if backend .env exists (required for Spotify API)
if [ ! -f "backend-openai/.env" ]; then
    echo "⚠️  Backend .env file not found. Please create it from env.example:"
    echo "   cp backend-openai/env.example backend-openai/.env"
    echo "   # Then edit backend-openai/.env with your credentials"
    exit 1
fi

# Create frontend .env if it doesn't exist
if [ ! -f "moodify-web/.env" ]; then
    echo "Creating frontend .env file..."
    echo "VITE_BACKEND_URL=http://localhost:8000" > moodify-web/.env
fi

# =============================================================================
# BACKEND SERVICE STARTUP
# =============================================================================

echo "\n🐍 Starting backend server..."
cd backend-openai

# Verify Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create it:"
    echo "   cd backend-openai"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and start FastAPI server
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cd ..

# =============================================================================
# FRONTEND SERVICE STARTUP
# =============================================================================

echo "\n⚛️  Starting frontend server..."
cd moodify-web

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start Vite development server with hot reloading
npm run dev &
FRONTEND_PID=$!

cd ..

# =============================================================================
# SERVICE STATUS AND HEALTH CHECK
# =============================================================================

echo "\n✅ Services starting up..."
echo "\n🔗 URLs:"
echo "   Frontend: http://127.0.0.1:5173"
echo "   Backend API: http://127.0.0.1:8000"
echo "   API Docs: http://127.0.0.1:8000/docs"
echo "\n⏳ Waiting for services to be ready..."

# Allow services time to initialize
sleep 5

# Run health check to verify services are responding
if [ -f "scripts/health-check.sh" ]; then
    ./scripts/health-check.sh
fi

# =============================================================================
# RUNTIME MONITORING
# =============================================================================

echo "\n🎵 Moodify is running! Press Ctrl+C to stop all services."
echo "\n📝 Logs will appear below:"
echo "=====================================\n"

# Wait for background processes to complete
wait