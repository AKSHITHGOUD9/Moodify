# Moodify - Music Discovery

**Transform your mood into the perfect playlist with AI-powered music recommendations using Spotify and advanced language models.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20Moodify-brightgreen)](https://moodify.akshithmothkuri.com)
[![Tech Stack](https://img.shields.io/badge/Tech%20Stack-React%20%7C%20FastAPI%20%7C%20OpenAI-blue)](https://github.com/AKSHITHGOUD9/Moodify-AI-Powered)

## 🌟 Features

- **AI-Powered Recommendations**: Uses OpenAI GPT-4o, Gemini, and Hugging Face for intelligent music curation
- **Smart History Filtering**: Analyzes your Spotify listening history to find relevant tracks
- **Multi-LLM Load Balancing**: Automatically routes queries to the best AI model
- **Real-time Playlist Creation**: Create and save playlists directly to Spotify
- **Beautiful Analytics Dashboard**: Spotify-inspired design with album cover backgrounds
- **Global Music Support**: Works with regional music (Tamil, Telugu, Hindi, etc.)

## 🚀 Live Demo

**Try it now:** [https://moodify.akshithmothkuri.com](https://moodify.akshithmothkuri.com)

## 📱 Demo Videos

### Demo 1: Getting Started & Login
**File:** `demos/01-login-demo.mp4`
**Description:** Complete walkthrough of Spotify OAuth login and initial setup

### Demo 2: AI-Powered Search & Recommendations  
**File:** `demos/02-ai-recommendations-demo.mp4`
**Description:** 
- Search for "chill old telugu songs"
- Watch AI generate specific song recommendations
- See how it filters from your listening history

### Demo 3: Analytics Dashboard
**File:** `demos/03-analytics-dashboard-demo.mp4`
**Description:**
- View your top tracks and artists
- See listening patterns with beautiful album cover backgrounds
- Explore your music profile

### Demo 4: Playlist Creation & Spotify Integration
**File:** `demos/04-playlist-creation-demo.mp4`
**Description:**
- Create custom playlists
- Save directly to Spotify
- Play recommendations through the app

### Demo 5: Regional Music & Advanced Features
**File:** `demos/05-regional-music-demo.mp4`
**Description:**
- Search for Tamil, Hindi, Telugu music
- Show AI's cultural understanding
- Demonstrate multi-language support

## 🛠️ Tech Stack

**Frontend:** React, Vite, CSS3  
**Backend:** FastAPI, Python 3.12  
**AI/ML:** OpenAI GPT-4o, Google Gemini, Hugging Face  
**APIs:** Spotify Web API  
**Deployment:** Vercel (Frontend), Render (Backend)  

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Spotify Developer Account
- OpenAI API Key (optional)
- Google Gemini API Key (optional)
- Hugging Face API Key (optional)

### 1. Clone the Repository
```bash
git clone https://github.com/AKSHITHGOUD9/Moodify-AI-Powered.git
cd Moodify-AI-Powered
```

### 2. Backend Setup
```bash
cd backend-openai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp env.example .env
```

### 3. Frontend Setup
```bash
cd ../moodify-web

# Install dependencies
npm install

# Copy environment template
cp env.txt .env
```

### 4. Get API Credentials

#### Spotify API (Required)
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add redirect URI: `http://localhost:8000/callback`
4. Copy Client ID and Client Secret

#### OpenAI API (Recommended)
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key

#### Google Gemini API (Optional)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

#### Hugging Face API (Optional)
1. Go to [Hugging Face Settings](https://huggingface.co/settings/tokens)
2. Create a new access token
3. Copy the token

### 5. Configure Environment Variables

#### Backend (.env)
```bash
# Spotify Configuration (Required)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback

# AI API Keys (At least one required)
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEYS=your_gemini_api_key
HUGGING_FACE_KEYS=your_huggingface_token

# CORS Configuration
FRONTEND_URLS=http://localhost:5173,http://127.0.0.1:5173
```

#### Frontend (.env)
```bash
VITE_BACKEND_URL=http://localhost:8000
```

### 6. Run the Application

#### Start Backend
```bash
cd backend-openai
python main.py
```
Backend will run on: http://localhost:8000

#### Start Frontend
```bash
cd moodify-web
npm run dev
```
Frontend will run on: http://localhost:5173

### 7. Access the Application
Open your browser and go to: http://localhost:5173

## 🎯 How It Works

1. **User Authentication**: Secure Spotify OAuth login
2. **Music Profile Analysis**: AI analyzes your listening history and preferences
3. **Smart Query Processing**: Multiple AI models generate specific search queries
4. **Intelligent Filtering**: Advanced algorithms filter recommendations based on mood, genre, and cultural context
5. **Playlist Creation**: Generate and save playlists directly to Spotify

## 🧠 AI Features

- **Multi-Model Architecture**: Routes queries to OpenAI, Gemini, or Hugging Face based on complexity
- **Cultural Understanding**: Specialized handling for regional music (Tamil, Telugu, Hindi, etc.)
- **Context-Aware Filtering**: Removes irrelevant content like background music or sound effects
- **Personalized Recommendations**: Uses your music DNA for better suggestions

## 📁 Project Structure

```
Moodify-AI-Powered/
├── backend-openai/          # FastAPI backend
│   ├── main.py             # Main application
│   ├── requirements.txt    # Python dependencies
│   └── .env               # Environment variables
├── moodify-web/            # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   └── App.jsx        # Main app component
│   ├── public/            # Static assets
│   └── .env              # Environment variables
├── demos/                 # Demo videos (add your videos here)
│   ├── 01-login-demo.mp4
│   ├── 02-ai-recommendations-demo.mp4
│   ├── 03-analytics-dashboard-demo.mp4
│   ├── 04-playlist-creation-demo.mp4
│   └── 05-regional-music-demo.mp4
└── README.md
```

## 🎬 Creating Demo Videos

### Video Specifications
- **Format**: MP4 (H.264 codec)
- **Resolution**: 1920x1080 (Full HD)
- **Frame Rate**: 30fps
- **Duration**: 2-3 minutes per demo
- **File Size**: Keep under 50MB per video

### Recording Tips
1. **Clear Audio**: Use good microphone, avoid background noise
2. **Smooth Scrolling**: Use slow, deliberate mouse movements
3. **Highlight Interactions**: Pause briefly after clicking buttons
4. **Show Results**: Wait for API responses to load completely
5. **Professional Narration**: Explain what's happening clearly

### Tools for Recording
- **Screen Recording**: OBS Studio, Loom, or QuickTime
- **Editing**: DaVinci Resolve (free) or Adobe Premiere Pro
- **Compression**: HandBrake (free) for optimizing file sizes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Spotify Web API for music data
- OpenAI, Google, and Hugging Face for AI capabilities
- React and FastAPI communities for excellent frameworks

## 📞 Contact

**Akshith Goud**  
- LinkedIn: [Your LinkedIn Profile]
- GitHub: [@AKSHITHGOUD9](https://github.com/AKSHITHGOUD9)
- Live Demo: [moodify.akshithmothkuri.com](https://moodify.akshithmothkuri.com)

---

⭐ **Star this repository if you found it helpful!**

*Built with ❤️ and AI*
