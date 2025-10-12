# Moodify - AI Music Discovery

A music recommendation app that uses AI to find songs based on your mood and preferences.

## What it does

- Connect your Spotify account
- Describe what music you want (like "chill rock songs" or "happy workout music")
- Get personalized recommendations from your listening history + new discoveries
- Create playlists directly in Spotify

## Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- Spotify Developer Account

### 1. Get Spotify API Keys

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add redirect URI: `http://localhost:8000/callback`
4. Copy your Client ID and Client Secret

### 2. Backend Setup

```bash
cd backend-openai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment file
cp env.example .env
```

Edit `.env` file with your Spotify credentials:
```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback
SESSION_SECRET=some_random_string_here
FRONTEND_URLS=http://localhost:5173,http://127.0.0.1:5173
POST_LOGIN_REDIRECT=http://localhost:5173/
```

### 3. Frontend Setup

```bash
cd ../moodify-web

# Install dependencies
npm install

# Create environment file
echo "VITE_BACKEND_URL=http://localhost:8000" > .env
```

### 4. Run the App

**Terminal 1 - Start Backend:**
```bash
cd backend-openai
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd moodify-web
npm run dev
```

Visit `http://localhost:5173` and start using the app!

## How it works

1. **Login with Spotify** - Connect your account to access your music history
2. **Describe what you want** - Type things like "chill old songs", "new tamil hits", "rock music"
3. **Get recommendations** - See relevant songs from your history + new discoveries
4. **Create playlists** - Save recommendations directly to your Spotify

## Features

- **Smart History Filtering** - Shows relevant songs from your listening history based on your query
- **AI-Powered Search** - Uses OpenAI to find new music that matches your request
- **Personalized Results** - Combines your music taste with your current mood
- **Direct Spotify Integration** - Create playlists without leaving the app

## Development Scripts

**Start both servers:**
```bash
./scripts/dev.sh
```

**Check if everything is running:**
```bash
./scripts/health-check.sh
```

## Deployment

### Backend (Render)
1. Connect your GitHub repo to Render
2. Set environment variables in Render dashboard
3. Deploy from `backend-openai` folder

### Frontend (Vercel)
1. Connect your GitHub repo to Vercel
2. Set build command: `npm run build`
3. Set root directory: `moodify-web`

## Project Structure

```
Moodify/
├── backend-openai/          # FastAPI backend
│   ├── main.py             # Main app file
│   ├── requirements.txt    # Python dependencies
│   └── venv/               # Virtual environment
├── moodify-web/            # React frontend
│   ├── src/                # Source code
│   └── package.json        # Dependencies
└── scripts/                # Helper scripts
```

## Troubleshooting

**Backend won't start:**
- Make sure virtual environment is activated
- Check if all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file has correct Spotify credentials

**Frontend won't start:**
- Make sure Node.js is installed
- Run `npm install` to install dependencies
- Check if backend is running on port 8000

**Spotify login issues:**
- Verify redirect URI matches exactly: `http://localhost:8000/callback`
- Make sure your Spotify app is in development mode
- Add your Spotify account to the app's user list in developer dashboard

## Tech Stack

- **Backend:** FastAPI, Spotipy, OpenAI
- **Frontend:** React, Vite
- **Deployment:** Render (backend), Vercel (frontend)

---

Made by [AKSHITHGOUD9](https://github.com/AKSHITHGOUD9)