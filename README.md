# 🎵 Moodify - AI-Powered Music Discovery

**Transform your emotions into the perfect playlist with cutting-edge AI technology.**

Moodify is an intelligent music recommendation system that analyzes your mood, preferences, and listening history to create personalized playlists that match your vibe perfectly. Using advanced natural language processing and Spotify's rich music data, Moodify understands what you're feeling and delivers the soundtrack to your life.

## ✨ Features

### 🤖 AI-Powered Recommendations
- **Natural Language Processing**: Describe your mood in plain English
- **Emotion Analysis**: Advanced algorithms detect genres, moods, and audio preferences
- **Smart Matching**: Combines your listening history with mood analysis for perfect recommendations

### 🎧 Spotify Integration
- **Seamless Authentication**: Secure OAuth2 integration with Spotify
- **Instant Playlist Creation**: Auto-generate playlists directly in your Spotify library
- **Rich Music Data**: Access to millions of tracks with detailed audio features

### 📊 Personal Analytics
- **Listening Insights**: Detailed analysis of your music taste and habits
- **Top Tracks & Artists**: See your most played content across different time periods
- **Genre Breakdown**: Understand your musical preferences with visual analytics
- **Recent Activity**: Track your listening patterns and discover trends

### 🎨 Modern Interface
- **Fluid Animations**: Beautiful, responsive design with smooth interactions
- **Dark Theme**: Eye-friendly interface perfect for any time of day
- **Mobile Responsive**: Optimized experience across all devices
- **Real-time Updates**: Live feedback and instant recommendations

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** for the backend
- **Node.js 16+** for the frontend
- **Spotify Developer Account** for API access

### 1. Clone the Repository
```bash
git clone https://github.com/AKSHITHGOUD9/Moodify-AI-Powered.git
cd Moodify-AI-Powered
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp env.txt .env
```

### 3. Configure Spotify API
1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Add redirect URI: `http://localhost:8000/callback`
4. Update your `.env` file:

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback
SESSION_SECRET=your_secure_session_secret
FRONTEND_URLS=http://localhost:5173,http://127.0.0.1:5173
POST_LOGIN_REDIRECT=http://localhost:5173/
```

### 4. Frontend Setup
```bash
# Navigate to frontend directory
cd ../moodify-web

# Install dependencies
npm install

# Create environment file
echo "VITE_BACKEND_URL=http://localhost:8000" > .env
```

### 5. Launch the Application
```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd moodify-web
npm run dev
```

Visit `http://localhost:5173` and start discovering music! 🎉

## 🏗️ Architecture

### Backend (FastAPI)
```
backend/
├── main.py              # Main application with all endpoints
├── requirements.txt     # Python dependencies
├── .env                # Environment configuration
└── venv/               # Virtual environment (excluded from git)
```

**Key Components:**
- **FastAPI Framework**: High-performance async web framework
- **Spotipy Integration**: Official Spotify Web API wrapper
- **Advanced Mood Analysis**: NLP-based emotion and genre detection
- **Session Management**: Secure user authentication and token handling
- **Audio Feature Mapping**: Intelligent matching of moods to audio characteristics

### Frontend (React + Vite)
```
moodify-web/
├── src/
│   ├── App.jsx          # Main application component
│   ├── App.css          # Comprehensive styling
│   ├── main.jsx         # Application entry point
│   └── components/
│       └── FluidCursor.jsx  # Advanced cursor animations
├── package.json         # Dependencies and scripts
├── vite.config.js       # Vite configuration
└── .env                # Environment variables
```

**Key Features:**
- **React 19**: Latest React with concurrent features
- **Vite Build Tool**: Lightning-fast development and building
- **Fluid Animations**: Custom CSS animations and transitions
- **Responsive Design**: Mobile-first approach with modern CSS Grid/Flexbox
- **Real-time Updates**: Live data fetching and state management

## 🎯 API Endpoints

### Authentication
- `GET /login` - Initiate Spotify OAuth flow
- `GET /callback` - Handle OAuth callback
- `GET /me` - Get current user profile

### Music Discovery
- `POST /recommend` - Generate AI-powered recommendations
- `POST /create-playlist` - Create custom playlists
- `GET /api/top-tracks` - Get user's top tracks and analytics
- `GET /api/my-playlists` - Retrieve user's playlists

### System
- `GET /` - API status and information
- `GET /health` - Health check endpoint

## 🧠 AI Algorithm

Moodify's recommendation engine combines multiple data sources:

1. **Natural Language Processing**
   - Tokenizes and analyzes user input
   - Maps emotions to musical characteristics
   - Identifies genres and mood keywords

2. **Audio Feature Analysis**
   - Energy, tempo, valence mapping
   - Danceability and acousticness factors
   - Dynamic range and loudness preferences

3. **User Profile Integration**
   - Historical listening patterns
   - Favorite genres and artists
   - Time-based preference analysis

4. **Intelligent Blending**
   - 70% query-based recommendations
   - 30% user preference weighting
   - Real-time adaptation to feedback

## 🎨 Design Philosophy

### Visual Design
- **Glassmorphism**: Translucent elements with backdrop blur
- **Fluid Animations**: Smooth, physics-based transitions
- **Dark Theme**: Reduced eye strain with elegant contrast
- **Minimalist Layout**: Clean, distraction-free interface

### User Experience
- **Intuitive Interaction**: Natural language input for music discovery
- **Instant Feedback**: Real-time loading states and animations
- **Progressive Enhancement**: Works great on all devices and connection speeds
- **Accessibility**: Keyboard navigation and screen reader support

## 🔧 Configuration

### Environment Variables

**Backend (.env)**
```env
# Spotify API Configuration
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback

# Security
SESSION_SECRET=your_secure_random_string

# CORS Configuration
FRONTEND_URLS=http://localhost:5173,http://127.0.0.1:5173

# Redirect Configuration
POST_LOGIN_REDIRECT=http://localhost:5173/
```

**Frontend (.env)**
```env
# Backend API URL
VITE_BACKEND_URL=http://localhost:8000
```

### Customization Options

**Mood Mappings**: Extend `GENRE_MAPPINGS` in `main.py` to add new mood categories
**Audio Features**: Modify `AUDIO_FEATURE_MAPPINGS` to adjust recommendation parameters
**UI Themes**: Customize CSS variables in `App.css` for different color schemes
**Animation Speed**: Adjust timing functions in CSS for different animation preferences

## 🚀 Deployment

### Production Setup

1. **Backend Deployment**
   ```bash
   # Install production dependencies
   pip install gunicorn

   # Run with Gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **Frontend Deployment**
   ```bash
   # Build for production
   npm run build

   # Serve static files (use your preferred method)
   npm run preview
   ```

3. **Environment Configuration**
   - Update `SPOTIFY_REDIRECT_URI` to your production domain
   - Set `FRONTEND_URLS` to your production frontend URL
   - Use secure `SESSION_SECRET` in production
   - Enable HTTPS for secure cookie handling

### Docker Support (Optional)
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Commit with descriptive messages: `git commit -m 'Add amazing feature'`
5. Push to your branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Contribution Guidelines
- **Code Style**: Follow PEP 8 for Python, ESLint for JavaScript
- **Testing**: Add tests for new features
- **Documentation**: Update README and code comments
- **Performance**: Ensure changes don't impact load times
- **Accessibility**: Maintain keyboard navigation and screen reader support

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Spotify Web API** - For providing comprehensive music data
- **FastAPI** - For the excellent async web framework
- **React Team** - For the powerful UI library
- **Vite** - For the blazing-fast build tool
- **Open Source Community** - For the amazing tools and libraries

## 📞 Support

Having issues? We're here to help!

- **GitHub Issues**: [Report bugs or request features](https://github.com/AKSHITHGOUD9/Moodify-AI-Powered/issues)
- **Documentation**: Check this README for detailed setup instructions
- **Community**: Join discussions in the Issues section

## 🔮 Roadmap

### Upcoming Features
- **Machine Learning Enhancement**: Advanced recommendation algorithms
- **Social Features**: Share playlists and discover friends' music
- **Voice Integration**: Voice commands for hands-free music discovery
- **Offline Mode**: Cache recommendations for offline access
- **Multi-Platform**: Mobile app development
- **Advanced Analytics**: Deeper insights into listening patterns

---

**Made with ❤️ by [AKSHITHGOUD9](https://github.com/AKSHITHGOUD9)**

*Discover music that matches your soul. Experience Moodify today.*