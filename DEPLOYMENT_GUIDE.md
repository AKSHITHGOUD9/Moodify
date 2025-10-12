# 🚀 Moodify Deployment Guide

Complete guide to deploy your AI-powered music discovery platform.

## 📁 Project Structure

```
Moodify/
├── backend-ollama/          # Local LLM Version (Ollama)
│   ├── main.py             # Backend application
│   ├── requirements.txt    # Python dependencies
│   └── env.example         # Environment template
├── backend-openai/          # OpenAI Version
│   ├── main.py             # Backend application
│   ├── requirements.txt    # Python dependencies
│   └── env.example         # Environment template
├── moodify-web/            # Frontend (React + Vite)
│   ├── src/                # React components
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
└── scripts/                # Deployment scripts
```

## 🎯 Choose Your Backend Version

### **Option 1: Local LLM (Ollama) - FREE**
- **Best for:** Development, privacy-focused users
- **Cost:** Free (runs locally)
- **Requirements:** Ollama installed locally

### **Option 2: OpenAI - CLOUD**
- **Best for:** Production, cloud deployment
- **Cost:** ~$2/month for 1000 requests
- **Requirements:** OpenAI API key

## 🔧 Local Development Setup

### **1. Prerequisites**
```bash
# Install Node.js (for frontend)
# Install Python 3.11+ (for backend)
# Install Ollama (if using Ollama version)
```

### **2. Setup Backend**

**For Ollama Version:**
```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Start Ollama
ollama serve

# Pull the model
ollama pull llama3.2:3b

# Setup backend
cd backend-ollama
cp env.example .env
# Edit .env with your Spotify credentials
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude "venv"
```

**For OpenAI Version:**
```bash
cd backend-openai
cp env.example .env
# Edit .env with your Spotify credentials and OpenAI API key
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude "venv"
```

### **3. Setup Frontend**
```bash
cd moodify-web
npm install
npm run dev
```

### **4. Configure Environment Variables**

**Backend `.env` (both versions need these):**
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/callback
FRONTEND_URLS=http://127.0.0.1:5173
POST_LOGIN_REDIRECT=http://127.0.0.1:5173/
SESSION_SECRET=your-random-secret-key
```

**Ollama version additional:**
```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

**OpenAI version additional:**
```env
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo
```

**Frontend `.env`:**
```env
VITE_BACKEND_URL=http://127.0.0.1:8000
```

## 🌐 Production Deployment

### **Option 1: Railway (Recommended)**

1. **Connect your GitHub repository to Railway**
2. **Choose your backend version:**
   - **Ollama:** Use `backend-ollama/` directory
   - **OpenAI:** Use `backend-openai/` directory

3. **Set environment variables in Railway dashboard:**
   - All the variables from your `.env` file
   - Add `PORT` variable (Railway will provide this)

4. **Deploy:**
   - Railway will automatically build and deploy
   - Your app will be available at `https://your-app.railway.app`

### **Option 2: Render**

1. **Create a new Web Service on Render**
2. **Connect your GitHub repository**
3. **Configure:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3.11

4. **Set environment variables in Render dashboard**
5. **Deploy**

### **Option 3: DigitalOcean App Platform**

1. **Create a new App on DigitalOcean**
2. **Connect your GitHub repository**
3. **Configure:**
   - **Source Directory:** `backend-ollama/` or `backend-openai/`
   - **Build Command:** `pip install -r requirements.txt`
   - **Run Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Set environment variables**
5. **Deploy**

## 🔑 Required API Keys

### **Spotify API Setup:**
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Get your `CLIENT_ID` and `CLIENT_SECRET`
4. Add redirect URIs:
   - `http://127.0.0.1:8000/callback` (development)
   - `https://your-domain.com/callback` (production)

### **OpenAI API Setup (if using OpenAI version):**
1. Go to [OpenAI Platform](https://platform.openai.com)
2. Create an API key
3. Add it to your environment variables

## 🎵 Features

### **✨ Frontend Features:**
- **Fluid animations** that respond to mouse movement
- **Interactive album cover grid** background
- **ChatGPT-style input** with smart suggestions
- **Modern analytics dashboard** with glassmorphism effects
- **Two-column recommendation layout**
- **Drag-and-drop track reordering**
- **Playlist creation** integration

### **🤖 AI Features:**
- **AI-powered music recommendations** based on your listening history
- **Intelligent track selection** from your music library
- **Spotify integration** for new discoveries
- **Personalized analytics** and insights

### **📊 Analytics:**
- **Top tracks analysis** (short/medium/long term)
- **Genre analysis** from listening patterns
- **Audio features analysis** (energy, tempo, valence, danceability)
- **Album cover grid** from your music history
- **Playlist management** and creation

## 🚀 Quick Start Commands

### **Development (Ollama):**
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
cd backend-ollama
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude "venv"

# Terminal 3: Start Frontend
cd moodify-web
npm run dev
```

### **Development (OpenAI):**
```bash
# Terminal 1: Start Backend
cd backend-openai
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude "venv"

# Terminal 2: Start Frontend
cd moodify-web
npm run dev
```

## 🎯 Production URLs

After deployment, your app will be available at:
- **Frontend:** `https://your-domain.com`
- **Backend API:** `https://your-domain.com/api`
- **Health Check:** `https://your-domain.com/health`

## 🔧 Troubleshooting

### **Common Issues:**

1. **401 Unauthorized errors:**
   - Make sure you're logged in through the frontend
   - Check that Spotify credentials are correct

2. **Album covers not loading:**
   - Verify Spotify API permissions
   - Check that user has music history

3. **Recommendations not working:**
   - For Ollama: Make sure Ollama is running and model is pulled
   - For OpenAI: Check API key and billing

4. **Frontend not connecting:**
   - Verify `VITE_BACKEND_URL` in frontend `.env`
   - Check CORS settings in backend

## 📝 Notes

- **Both backend versions** have identical API endpoints
- **Frontend works with both** versions without changes
- **Easy switching** between Ollama and OpenAI
- **All features preserved** across both versions
- **Production-ready** implementations

## 🎵 Enjoy Your Music Discovery App!

Your Moodify app is now ready to help users discover their next favorite songs with AI-powered recommendations! 🎵✨
