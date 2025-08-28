#!/bin/bash

# Moodify Health Check Script
# Checks if both backend and frontend are running properly

set -e

echo "🏥 Moodify Health Check"
echo "====================="

# Check backend
echo "\n🔍 Checking backend (http://localhost:8000)..."
if curl -s -f "http://localhost:8000/" > /dev/null; then
    echo "✅ Backend is running"
    
    # Check if backend returns proper JSON
    response=$(curl -s "http://localhost:8000/")
    if echo "$response" | grep -q "Moodify"; then
        echo "✅ Backend API is responding correctly"
    else
        echo "⚠️  Backend is running but may not be responding correctly"
    fi
else
    echo "❌ Backend is not responding"
    echo "   Make sure to start it with: cd backend && uvicorn main:app --reload"
fi

# Check frontend
echo "\n🔍 Checking frontend (http://localhost:5173)..."
if curl -s -f "http://localhost:5173/" > /dev/null; then
    echo "✅ Frontend is running"
else
    echo "❌ Frontend is not responding"
    echo "   Make sure to start it with: cd moodify-web && npm run dev"
fi

# Check if both are running
backend_running=$(curl -s -f "http://localhost:8000/" > /dev/null && echo "true" || echo "false")
frontend_running=$(curl -s -f "http://localhost:5173/" > /dev/null && echo "true" || echo "false")

if [ "$backend_running" = "true" ] && [ "$frontend_running" = "true" ]; then
    echo "\n🎉 All services are running! Visit http://localhost:5173 to use Moodify"
else
    echo "\n⚠️  Some services are not running. Please check the logs above."
fi

echo "\n📊 System Information:"
echo "   Node.js: $(node --version 2>/dev/null || echo 'Not installed')"
echo "   Python: $(python3 --version 2>/dev/null || echo 'Not installed')"
echo "   npm: $(npm --version 2>/dev/null || echo 'Not installed')"