#!/bin/bash

# Moodify Development Startup Script
# Starts both backend and frontend in development mode

set -e

echo "🎵 Starting Moodify in Development Mode"
echo "====================================="

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "moodify-web" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo "\n🛑 Shutting down services..."
    jobs -p | xargs -r kill
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Check if backend .env exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Backend .env file not found. Please run setup first:"
    echo "   ./scripts/deploy.sh"
    exit 1
fi

# Check if frontend .env exists
if [ ! -f "moodify-web/.env" ]; then
    echo "Creating frontend .env file..."
    echo "VITE_BACKEND_URL=http://localhost:8000" > moodify-web/.env
fi

echo "\n🐍 Starting backend server..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   ./scripts/deploy.sh"
    exit 1
fi

# Start backend in background
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cd ..

echo "\n⚛️  Starting frontend server..."
cd moodify-web

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
npm run dev &
FRONTEND_PID=$!

cd ..

echo "\n✅ Services starting up..."
echo "\n🔗 URLs:"
echo "   Frontend: http://127.0.0.1:5173"
echo "   Backend API: http://127.0.0.1:8000"
echo "   API Docs: http://127.0.0.1:8000/docs"
echo "\n⏳ Waiting for services to be ready..."

# Wait a bit for services to start
sleep 5

# Run health check
if [ -f "scripts/health-check.sh" ]; then
    ./scripts/health-check.sh
fi

echo "\n🎵 Moodify is running! Press Ctrl+C to stop all services."
echo "\n📝 Logs will appear below:"
echo "=====================================\n"

# Wait for background processes
wait