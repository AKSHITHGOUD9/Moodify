#!/bin/bash

"""
Moodify Health Check Script
===========================

This script performs comprehensive health checks on both the backend and frontend
services to ensure they are running properly and responding to requests.

Features:
- Backend API endpoint validation
- Frontend service availability check
- Response content verification
- System dependency reporting
- Detailed error reporting and troubleshooting

Usage:
    ./scripts/health-check.sh

Author: Moodify Development Team
Version: 1.0.0
"""

set -e  # Exit on any error

echo "🏥 Moodify Health Check"
echo "====================="

# =============================================================================
# BACKEND HEALTH CHECK
# =============================================================================

echo "\n🔍 Checking backend (http://127.0.0.1:8000)..."
if curl -s -f "http://127.0.0.1:8000/" > /dev/null; then
    echo "✅ Backend is running"
    
    # Verify backend returns proper response content
    response=$(curl -s "http://127.0.0.1:8000/")
    if echo "$response" | grep -q "Moodify"; then
        echo "✅ Backend API is responding correctly"
    else
        echo "⚠️  Backend is running but may not be responding correctly"
    fi
else
    echo "❌ Backend is not responding"
    echo "   Make sure to start it with: cd backend && uvicorn main:app --reload --host 127.0.0.1"
fi

# =============================================================================
# FRONTEND HEALTH CHECK
# =============================================================================

echo "\n🔍 Checking frontend (http://127.0.0.1:5173)..."
if curl -s -f "http://127.0.0.1:5173/" > /dev/null; then
    echo "✅ Frontend is running"
else
    echo "❌ Frontend is not responding"
    echo "   Make sure to start it with: cd moodify-web && npm run dev"
fi

# =============================================================================
# OVERALL SYSTEM STATUS
# =============================================================================

# Determine overall system health status
backend_running=$(curl -s -f "http://127.0.0.1:8000/" > /dev/null && echo "true" || echo "false")
frontend_running=$(curl -s -f "http://127.0.0.1:5173/" > /dev/null && echo "true" || echo "false")

if [ "$backend_running" = "true" ] && [ "$frontend_running" = "true" ]; then
    echo "\n🎉 All services are running! Visit http://127.0.0.1:5173 to use Moodify"
else
    echo "\n⚠️  Some services are not running. Please check the logs above."
fi

# =============================================================================
# SYSTEM INFORMATION REPORT
# =============================================================================

echo "\n📊 System Information:"
echo "   Node.js: $(node --version 2>/dev/null || echo 'Not installed')"
echo "   Python: $(python3 --version 2>/dev/null || echo 'Not installed')"
echo "   npm: $(npm --version 2>/dev/null || echo 'Not installed')"