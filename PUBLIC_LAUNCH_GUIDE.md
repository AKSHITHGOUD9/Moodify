# 🚀 Moodify Public Launch Guide

## 📋 Pre-Launch Checklist

### ✅ **1. Spotify App Configuration**

#### **Option A: Quick Launch (Up to 25 Users)**
- [ ] Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- [ ] Open your app (Client ID: 7852418069c743a48f5190e7a940d415)
- [ ] Go to "Users and Access" → Add user emails (max 25)
- [ ] Save changes

#### **Option B: Public Launch (Unlimited Users)**
- [ ] Go to your Spotify app dashboard
- [ ] Navigate to "Settings" → "Quota Extension"
- [ ] Click "Request Extension"
- [ ] Fill out the form:
  ```
  App Name: Moodify
  Use Case: AI-powered music recommendation platform that helps users 
            discover new music based on their listening history using 
            OpenAI GPT for intelligent track curation
  Expected Monthly Users: [Your estimate]
  Commercial Use: [Yes/No]
  ```
- [ ] Submit and wait 1-2 weeks for approval
- [ ] Once approved, your app works for ALL Spotify users

---

## 🌐 Deployment Options

### **🚂 Option 1: Railway (Recommended - Easiest)**

**Cost**: ~$5-10/month | **Setup Time**: 15 minutes

#### **Step 1: Prepare Your Code**
```bash
# Push your code to GitHub
cd /Users/akshith/Desktop/Moodify
git add .
git commit -m "Prepare for public launch"
git push origin main
```

#### **Step 2: Deploy Backend on Railway**
1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your Moodify repository
5. Choose **root directory** and then select `backend-openai/`
6. Add environment variables:
   ```env
   SPOTIFY_CLIENT_ID=7852418069c743a48f5190e7a940d415
   SPOTIFY_CLIENT_SECRET=f8d5055113ca4e23814c7b2a7b378afd
   SPOTIFY_REDIRECT_URI=https://YOUR-APP.railway.app/callback
   OPENAI_API_KEY=YOUR_OPENAI_API_KEY
   OPENAI_MODEL=gpt-3.5-turbo
   SESSION_SECRET=your-super-secret-key-change-this
   FRONTEND_URLS=https://YOUR-FRONTEND.vercel.app
   POST_LOGIN_REDIRECT=https://YOUR-FRONTEND.vercel.app/
   PORT=8000
   ```
7. Click "Deploy"
8. Wait for deployment (2-3 minutes)
9. Copy your Railway URL: `https://your-app.railway.app`

#### **Step 3: Deploy Frontend on Vercel**
1. Go to [Vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Click "Add New" → "Project"
4. Select your Moodify repository
5. Set **Root Directory** to `moodify-web/`
6. Add environment variable:
   ```env
   VITE_BACKEND_URL=https://your-app.railway.app
   ```
7. Click "Deploy"
8. Wait for deployment (1-2 minutes)
9. Copy your Vercel URL: `https://your-app.vercel.app`

#### **Step 4: Update Spotify Redirect URIs**
1. Go back to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Open your app settings
3. Add these Redirect URIs:
   - `http://127.0.0.1:8000/callback` (keep for local dev)
   - `https://your-app.railway.app/callback` (production)
4. Save changes

#### **Step 5: Update Railway Environment Variables**
1. Go back to Railway dashboard
2. Update these variables with correct URLs:
   ```env
   SPOTIFY_REDIRECT_URI=https://your-app.railway.app/callback
   FRONTEND_URLS=https://your-app.vercel.app
   POST_LOGIN_REDIRECT=https://your-app.vercel.app/
   ```
3. Save and redeploy

✅ **Done!** Your app is live at `https://your-app.vercel.app`

---

### **🌊 Option 2: Render (Alternative)**

**Cost**: Free tier available, $7/month for production | **Setup Time**: 20 minutes

#### **Step 1: Deploy Backend**
1. Go to [Render.com](https://render.com)
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   ```
   Name: moodify-backend
   Region: Oregon (or closest to your users)
   Branch: main
   Root Directory: backend-openai
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
6. Add environment variables (same as Railway)
7. Choose **Free** or **Starter** plan
8. Click "Create Web Service"

#### **Step 2: Deploy Frontend**
1. Click "New" → "Static Site"
2. Connect your repository
3. Configure:
   ```
   Name: moodify-frontend
   Branch: main
   Root Directory: moodify-web
   Build Command: npm install && npm run build
   Publish Directory: dist
   ```
4. Add environment variable:
   ```env
   VITE_BACKEND_URL=https://your-backend.onrender.com
   ```
5. Click "Create Static Site"

#### **Step 3: Update Spotify & Environment Variables**
- Same as Railway steps 4 & 5

---

### **🐳 Option 3: DigitalOcean App Platform**

**Cost**: $5-12/month | **Setup Time**: 25 minutes

#### **Deploy**
1. Go to [DigitalOcean](https://www.digitalocean.com)
2. Create new App
3. Connect GitHub repository
4. Configure backend component:
   ```
   Source Directory: backend-openai
   Build Command: pip install -r requirements.txt
   Run Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Configure frontend component:
   ```
   Source Directory: moodify-web
   Build Command: npm install && npm run build
   Output Directory: dist
   ```
6. Add environment variables
7. Deploy

---

## 🔒 Security Checklist

Before going public, ensure:

- [ ] Change `SESSION_SECRET` to a strong random value:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] Never commit `.env` files to Git
- [ ] Keep your OpenAI API key secure
- [ ] Set up rate limiting (already implemented in your backend)
- [ ] Enable HTTPS (automatic with Vercel/Railway/Render)
- [ ] Review CORS settings in your backend

---

## 💰 Cost Breakdown

### **Recommended Setup: Vercel + Railway**
- **Frontend (Vercel)**: $0/month (Free tier covers most apps)
- **Backend (Railway)**: ~$5-10/month (depends on usage)
- **OpenAI API**: ~$2-5/month for 1000-5000 requests
- **Total**: ~$7-15/month

### **Alternative: Render**
- **Backend**: $0/month (Free) or $7/month (Production)
- **Frontend**: $0/month (Free)
- **OpenAI API**: ~$2-5/month
- **Total**: ~$2-12/month

### **Scale Estimates**
- **100 users/day**: ~$10-15/month
- **1,000 users/day**: ~$30-50/month
- **10,000 users/day**: ~$200-300/month

---

## 📱 Custom Domain (Optional)

### **Add Custom Domain to Vercel**
1. Buy domain from Namecheap/GoDaddy (~$10-15/year)
2. Go to Vercel dashboard → Domains
3. Add your domain (e.g., `moodify.app`)
4. Update DNS records as instructed by Vercel
5. SSL automatically provisioned ✅

### **Update Spotify Redirect URI**
```
https://moodify.app/callback
```

---

## 🧪 Testing Before Launch

### **1. Test Backend Health**
```bash
curl https://your-app.railway.app/health
# Should return: {"status":"healthy"}
```

### **2. Test Frontend Connection**
- Open `https://your-app.vercel.app`
- Should see the Moodify interface
- Click "Login with Spotify"
- Should redirect to Spotify auth

### **3. Test Full Flow**
1. Login with your Spotify account
2. View analytics dashboard
3. Generate recommendations
4. Create a playlist

---

## 📊 Monitoring & Analytics

### **Built-in Health Checks**
- Backend health: `https://your-app.railway.app/health`
- View logs in Railway/Render/DigitalOcean dashboard

### **Recommended Tools (Optional)**
- **Sentry**: Error tracking (free tier available)
- **PostHog**: User analytics (free tier available)
- **Better Uptime**: Uptime monitoring (free tier available)

---

## 🚀 Launch Day Checklist

- [ ] All services deployed and tested
- [ ] Custom domain configured (if using)
- [ ] Spotify app configured with production URLs
- [ ] Extended quota approved (if going fully public)
- [ ] Environment variables set correctly
- [ ] Test login flow end-to-end
- [ ] Test recommendations generation
- [ ] Test playlist creation
- [ ] Share link with friends for beta testing
- [ ] Monitor logs for any errors
- [ ] Announce on social media! 🎉

---

## 🎯 Post-Launch

### **Week 1**
- Monitor error logs daily
- Gather user feedback
- Fix any critical bugs

### **Week 2-4**
- Implement user feedback
- Optimize performance based on usage patterns
- Consider adding new features

### **Growth**
- Share on Reddit (r/spotify, r/musicproduction, r/webdev)
- Post on Product Hunt
- Share on Twitter/LinkedIn
- Create demo video for YouTube

---

## 🆘 Troubleshooting

### **"403 Forbidden" from Spotify**
→ User not added to Spotify app or Extended Quota not approved

### **"Cannot connect to backend"**
→ Check CORS settings, verify `FRONTEND_URLS` environment variable

### **"OpenAI API Error"**
→ Check API key, verify billing is enabled on OpenAI account

### **"No recommendations"**
→ Check user has Spotify history, verify OpenAI is responding

---

## 📞 Need Help?

- **Spotify API Issues**: [Spotify Developer Forum](https://community.spotify.com/t5/Spotify-for-Developers/bd-p/Spotify_Developer)
- **OpenAI Issues**: [OpenAI Help Center](https://help.openai.com)
- **Deployment Issues**: Check Railway/Vercel/Render docs

---

## 🎵 You're Ready to Launch! 

Your AI-powered music discovery platform is ready to help the world discover their next favorite songs! 🚀✨

**Next Step**: Choose your deployment platform and follow the steps above. Start with Railway + Vercel for the smoothest experience!

