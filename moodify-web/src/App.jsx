import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import "./App.css";

import AlbumCoverGrid from "./components/AlbumCoverGrid";
import RecommendationGridV2 from "./components/RecommendationGridV2";

const API = import.meta.env.VITE_BACKEND_URL;

// Elegant single quote
const ELEGANT_QUOTE = "Your emotions, our algorithms, pure magic";


// Main App Component
export default function App() {

  // =========================================================================
  // STATE MANAGEMENT
  // Manages all component state variables
  // =========================================================================
  const [me, setMe] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showRaw, setShowRaw] = useState(false);
  const [mood, setMood] = useState("");
  const [recs, setRecs] = useState([]);
  const [trackIds, setTrackIds] = useState([]);
  const [recsErr, setRecsErr] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [typingTimeout, setTypingTimeout] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [playlists, setPlaylists] = useState(null);
  const [loadingPlaylists, setLoadingPlaylists] = useState(false);
  const [createPlaylist, setCreatePlaylist] = useState(false);
  const [playlistName, setPlaylistName] = useState("");
  const [useNewRecommendationSystem, setUseNewRecommendationSystem] = useState(true);
  const [recommendationData, setRecommendationData] = useState(null);
  const [spotifyToken, setSpotifyToken] = useState(null);

  // =========================================================================
  // DATA FETCHING & LOGIC
  // Handles all API calls and core application logic
  // =========================================================================
  
  // Handle token from URL after Spotify authentication
  useEffect(() => {
    console.log("App.jsx: Token handling useEffect running");
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const userId = urlParams.get('user_id');
    
    console.log("App.jsx: URL params - token:", token ? "present" : "none", "userId:", userId ? "present" : "none");
    
    if (token) {
      console.log("App.jsx: Token found in URL, setting up token-based auth");
      setSpotifyToken(token);
      localStorage.setItem('spotify_token', token);
      if (userId) {
        localStorage.setItem('spotify_user_id', userId);
      }
      
      // Clear any existing errors when token becomes available
      setRecsErr("");
      
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // Fetch user data with token
      fetchUserDataWithToken(token);
    } else {
      // Try to get token from localStorage
      const storedToken = localStorage.getItem('spotify_token');
      console.log("App.jsx: No token in URL, checking localStorage:", storedToken ? "token found" : "no token");
      if (storedToken) {
        setSpotifyToken(storedToken);
        // Clear any existing errors when token becomes available
        setRecsErr("");
        // Fetch user data with stored token
        fetchUserDataWithToken(storedToken);
      }
    }
  }, []);

  const fetchUserDataWithToken = async (token) => {
    console.log("Fetching user data with token:", token ? "Token present" : "No token");
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      const res = await fetch(`${API}/me?token=${token}`, { 
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (res.ok) {
        const data = await res.json();
        setMe(data);
        setErr("");
      } else {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
    } catch (error) {
      console.error("Error fetching user data:", error);
      setErr(error.message);
    } finally {
      setLoading(false);
    }
  };
  const login = useCallback(() => {
    // Add timestamp to force fresh authentication
    const timestamp = Date.now();
    window.location.href = `${API}/login?t=${timestamp}`;
  }, []);

  const loadMe = useCallback(async () => {
    // If we have a token, use the token-based function instead
    if (spotifyToken) {
      return fetchUserDataWithToken(spotifyToken);
    }
    
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
      
      const res = await fetch(`${API}/me`, { 
        credentials: "include",
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMe(data);
      setErr("");
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      if (e.name === 'AbortError') {
        setErr('Request timeout - please try again');
      } else {
        setErr(String(e));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      // Call logout endpoint to clear session
      await fetch(`${API}/logout`, { 
        method: "POST", 
        credentials: "include" 
      });
      
      // Clear local state
      setMe(null);
      setShowProfile(false);
      setRecs([]);
      setTrackIds([]);
      setAnalytics(null);
      setPlaylists(null);
      setRecommendationData(null);
      setErr("");
      setSpotifyToken(null);
      
      // Clear localStorage
      localStorage.removeItem('spotify_token');
      localStorage.removeItem('spotify_user_id');
      
      // Show success message
      alert("Successfully logged out!");
    } catch (e) {
      console.error("Error during logout:", e);
      alert("Error during logout. Please try again.");
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    setLoadingAnalytics(true);
    try {
      const res = await fetch(`${API}/api/top-tracks`, { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAnalytics(data);
    } catch (e) {
      console.error("Failed to load analytics:", e);
      setAnalytics({ error: "Failed to load analytics data" });
    } finally {
      setLoadingAnalytics(false);
    }
  }, []);

  const loadPlaylists = useCallback(async () => {
    setLoadingPlaylists(true);
    try {
      const res = await fetch(`${API}/api/my-playlists`, { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPlaylists(data);
    } catch (e) {
      console.error("Failed to load playlists:", e);
      setPlaylists({ error: "Failed to load playlists" });
    } finally {
      setLoadingPlaylists(false);
    }
  }, []);


  const toggleDashboard = useCallback(() => {
    if (!showDashboard && !analytics) {
      loadAnalytics();
    }
    setShowDashboard(!showDashboard);
  }, [showDashboard, analytics, loadAnalytics]);

  /**
   * Generates track recommendations based on user mood.
   * Note: This function no longer auto-creates a playlist. It only fetches track data.
   */
  const generateRecs = useCallback(async () => {
    if (!mood.trim()) return;
    
    // Don't make requests if we don't have a token
    if (!spotifyToken) {
      setRecsErr("Please wait for authentication to complete");
      return;
    }

    setIsGenerating(true);
    setRecsErr("");
    setRecs([]);
    setTrackIds([]);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
      
      const url = spotifyToken ? `${API}/recommend-v2?token=${spotifyToken}` : `${API}/recommend-v2`;
      console.log("Making recommendation request to:", url);
      console.log("Spotify token present:", !!spotifyToken);
      
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        signal: controller.signal,
        body: JSON.stringify({
          query: mood.trim(),
          create_playlist: false, // Explicitly set to false
        }),
      });
      
      console.log("Recommendation response status:", res.status, res.statusText);
      
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      console.log("Recommendation response data:", data);
      setRecs(data);
      
      // Store the track IDs for later playlist creation
      if (data.tracks?.length > 0) {
        const ids = data.tracks.map(track => track.id);
        console.log("Setting track IDs:", ids);
        setTrackIds(ids);
      } else {
        console.log("No tracks found in response:", data);
      }
      
    } catch (e) {
      if (e.name === 'AbortError') {
        setRecsErr('Request timeout - please try a shorter query');
      } else {
        setRecsErr(String(e));
      }
    } finally {
      setIsGenerating(false);
    }
  }, [mood, spotifyToken]);

  // Memoized tracks to use for playlist creation
  const tracksToUse = useMemo(() => {
    if (useNewRecommendationSystem && recommendationData) {
      return recommendationData.getSelectedTrackIds ? recommendationData.getSelectedTrackIds() : [];
    }
    return trackIds;
  }, [useNewRecommendationSystem, recommendationData, trackIds]);

  /**
   * Creates a Spotify playlist from the currently loaded recommendations.
   * This is a user-initiated action.
   */
  const createPlaylistFromRecs = async () => {
    if (tracksToUse.length === 0) {
      alert("No tracks selected for the playlist. Please select some songs first.");
      return;
    }
    
    try {
      const playlistData = {
        name: playlistName.trim() || `Moodify Playlist for "${mood}"`,
        description: `AI-generated playlist based on: ${mood}`,
        track_ids: tracksToUse,
      };
      
      const res = await fetch(`${API}/create-playlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(playlistData),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      alert(`🎵 Playlist created successfully!\n\nName: ${data.playlist.name}\nTracks: ${data.playlist.tracks_added}\n\nCheck your Spotify library!`);
      
    } catch (e) {
      console.error("Failed to create playlist:", e);
      alert("Failed to create playlist. Please try again.");
    }
  };

  const handleRecommendationsGenerated = (data) => {
    setRecommendationData(data);
  };

  // Memoized filtered suggestions for better performance

  // Search suggestions handling
  const handleSearchInputChange = useCallback((e) => {
    const value = e.target.value;
    setMood(value);
    setIsTyping(value.trim().length > 0);
    
    // Clear existing timeout
    if (typingTimeout) {
      clearTimeout(typingTimeout);
    }
    
    if (value.trim().length > 0) {
      // Set timeout to hide AI button after user stops typing
      const timeout = setTimeout(() => {
        setIsTyping(false);
      }, 1000);
      setTypingTimeout(timeout);
    } else {
      // Clear recommendations when search is cleared
      setRecs([]);
      setTrackIds([]);
      setRecommendationData(null);
    }
  }, [typingTimeout]);


  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && mood.trim() && !isGenerating) {
      generateRecs();
    }
  }, [mood, isGenerating]);


  // =========================================================================
  // UI EFFECTS
  // Handles non-rendering side effects like API calls on component mount
  // =========================================================================
  useEffect(() => {
    // Only call loadMe if we don't have a token (token-based loading is handled separately)
    if (!spotifyToken) {
      loadMe();
    }
  }, [spotifyToken]);



  // =========================================================================
  // COMPONENT RENDERING
  // Defines the component's UI structure
  // =========================================================================
  console.log("App.jsx: Rendering component - me:", me ? "logged in" : "not logged in", "loading:", loading, "error:", err);
  console.log("App.jsx: Build timestamp:", new Date().toISOString());
  
  return (
    <div className="app-container">
      {/* Advanced Fluid Cursor Animation */}
      <AlbumCoverGrid />

      {/* Main content */}
      <div className="content">
        {/* Ultra Transparent Header */}
        <header className="ultra-transparent-header">
          <div className="transparent-logo">
            <span className="logo-gradient">Moodify</span>
          </div>

          {me && (
            <div className="transparent-nav">
              <button className="ghost-btn" onClick={toggleDashboard}>
                Your Dashboard
              </button>
              <div className="ghost-profile" onClick={() => setShowProfile(!showProfile)}>
                <div className="ghost-avatar">
                  {me.images?.[0]?.url ? (
                    <img src={me.images[0].url} alt="Profile" />
                  ) : (
                    <div className="avatar-circle">{me.display_name?.[0]}</div>
                  )}
                </div>
                <span className="ghost-name">{me.display_name}</span>
              </div>
            </div>
          )}
        </header>

        {/* Main content area */}
        <main className="main-content">
          {!me ? (
            <div className="login-section">
              <div className="login-card">
                <h2 className="section-title">Welcome to Moodify</h2>
                <p className="section-subtitle">AI-powered music discovery</p>
                <button className="login-button" onClick={login}>
                  <span className="button-text">Connect with Spotify</span>
                  <div className="button-glow"></div>
                </button>
                {err && <p className="error-message">{err}</p>}
              </div>
            </div>
          ) : (
            <>
              {/* Ultra Transparent Search Section */}
              <section className="invisible-section">
                <div className="center-content">
                  <h2 className="main-title">🎵 What's Your Vibe?</h2>
                  <div className="quote-container">
                    <p className="floating-quote">{ELEGANT_QUOTE}</p>
                  </div>
                </div>

                <div className="ghost-search-area">
                  <div className="chatgpt-input-wrapper">
                    <input
                      value={mood}
                      onChange={handleSearchInputChange}
                      placeholder="Ask me anything..."
                      className="chatgpt-input"
                      onKeyDown={handleKeyDown}
                    />
                    <button
                      className={`play-pause-btn ${isGenerating ? 'loading' : isTyping ? 'pause' : 'play'}`}
                      onClick={isGenerating ? () => setIsGenerating(false) : (mood.trim() ? generateRecs : null)}
                      disabled={!mood.trim() && !isGenerating}
                      title={isGenerating ? "Stop generation" : isTyping ? "Pause typing" : "Start search"}
                    >
                      {isGenerating ? (
                        <div className="loading-animation">
                          <div className="loading-dot"></div>
                          <div className="loading-dot"></div>
                          <div className="loading-dot"></div>
                        </div>
                      ) : isTyping ? (
                        <div className="pause-animation">
                          <div className="pause-bar"></div>
                          <div className="pause-bar"></div>
                        </div>
                      ) : (
                        <div className="play-animation">
                          <div className="play-triangle"></div>
                        </div>
                      )}
                    </button>
                    
                  </div>

                  {/* Invisible Playlist Options - Hidden while typing */}
                  {!isTyping && (
                    <div className="ghost-options">
                      <div className="toggle-area">
                        <label className="invisible-toggle">
                          <input
                            type="checkbox"
                            checked={useNewRecommendationSystem}
                            onChange={(e) => setUseNewRecommendationSystem(e.target.checked)}
                          />
                          <span className="ghost-slider"></span>
                          <span className="toggle-text">
                            Use AI + Spotify system
                            <span className="info-icon-wrapper">
                              <img src="/tooltip.png" alt="Info" className="info-icon" />
                              <div className="info-tooltip">
                                <div className="tooltip-content">
                                  <div className="tooltip-section">
                                    <strong>AI + Spotify:</strong> Advanced AI analysis of your music history for personalized recommendations.
                                  </div>
                                  <div className="tooltip-section">
                                    <strong>Regular Backend:</strong> Traditional algorithms based on audio features and genre matching.
                                  </div>
                                </div>
                              </div>
                            </span>
                          </span>
                        </label>
                      </div>
                    </div>
                  )}
                </div>

                {recsErr && <p className="ghost-error">{recsErr}</p>}
              </section>

              {/* Recommendations section */}
              {mood.trim() && (
                <section className="recommendations-section">
                  {useNewRecommendationSystem ? (
                    <RecommendationGridV2 
                      query={mood} 
                      onRecommendationsGenerated={handleRecommendationsGenerated}
                    />
                  ) : (
                    // Old recommendation system
                    (recs.tracks?.length > 0 || recs.length > 0) && (
                      <>
                        <h3 className="section-title">✨ Your AI-Generated Playlist</h3>

                        {/* AI Analysis Display */}
                        {recs.analysis && (
                          <div className="ai-analysis">
                            <div className="analysis-card">
                              <h4>🤖 AI Analysis</h4>
                              <p className="analysis-text">{recs.analysis.analysis_text}</p>
                              <div className="analysis-details">
                                {recs.analysis.detected_genres.length > 0 && (
                                  <div className="analysis-item">
                                    <span className="label">Genres: </span>
                                    <span className="value">{recs.analysis.detected_genres.join(", ")}</span>
                                  </div>
                                )}
                                {recs.analysis.detected_moods.length > 0 && (
                                  <div className="analysis-item">
                                    <span className="label">Mood:</span>
                                    <span className="value">{recs.analysis.detected_moods.join(", ")}</span>
                                  </div>
                                )}
                                <div className="analysis-item">
                                  <span className="label">Confidence: </span>
                                  <span className="value">{Math.round(recs.analysis.confidence * 100)}%</span>
                                </div>
                              </div>
                            </div>

                            {/* Your Music Profile */}
                            {recs.user_profile && recs.user_profile.top_genres && (
                              <div className="analysis-card">
                                <h4>🎵 Your Music Profile</h4>
                                <div className="profile-details">
                                  <div className="profile-item">
                                    <span className="label">Top Genres:</span>
                                    <span className="value">{recs.user_profile.top_genres.slice(0, 3).join(", ")}</span>
                                  </div>
                                  <div className="profile-item">
                                    <span className="label">Tracks Analyzed:</span>
                                    <span className="value">{recs.user_profile.total_tracks_analyzed}</span>
                                  </div>
                                  {recs.user_profile.avg_audio_features && (
                                    <div className="profile-item">
                                      <span className="label">Your Energy Level:</span>
                                      <span className="value">{Math.round(recs.user_profile.avg_audio_features.energy * 100)}%</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        <div className="tracks-grid">
                          {(recs.tracks || recs).map((track) => (
                            <div key={track.id} className="track-card">
                              <div className="track-image">
                                {track.album_image ? (
                                  <img src={track.album_image} alt={track.name} />
                                ) : (
                                  <div className="image-placeholder">
                                    <span>🎵</span>
                                  </div>
                                )}
                                <div className="track-overlay">
                                  {track.preview_url && (
                                    <audio controls src={track.preview_url} className="track-preview">
                                      Your browser does not support the audio element.
                                    </audio>
                                  )}
                                </div>
                              </div>

                              <div className="track-info">
                                <h4 className="track-name">{track.name}</h4>
                                <p className="track-artist">{(track.artists || []).join(", ")}</p>
                                {track.popularity && (
                                  <div className="track-popularity">
                                    <span className="popularity-label">Popularity:</span>
                                    <div className="popularity-bar">
                                      <div
                                        className="popularity-fill"
                                        style={{ width: `${track.popularity}%` }}
                                      ></div>
                                    </div>
                                  </div>
                                )}
                              </div>

                              {track.external_url && (
                                <a
                                  href={track.external_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="spotify-link"
                                >
                                  Open in Spotify
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    )
                  )}

                  {/* Playlist Creation Button */}
                  <div style={{ textAlign: "center", margin: "2rem auto" }}>
                    <button
                      className="login-button" 
                      onClick={createPlaylistFromRecs}
                      disabled={isGenerating || (useNewRecommendationSystem ? !recommendationData?.getSelectedTrackIds?.()?.length : !trackIds.length)}
                    >
                      Create Playlist on Spotify
                    </button>
                  </div>
                </section>
              )}
            </>
          )}
        </main>
      </div>

      {/* Revamped Analytics Dashboard */}
      {showDashboard && (
        <div className="modern-dashboard-overlay">
          <div className="modern-dashboard-container">
            {/* Enhanced Header */}
            <div className="modern-dashboard-header">
              <div className="header-left">
                <h1 className="dashboard-title">
                  <span className="title-icon">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                      <path d="M3 13h2v8H3v-8zm4-6h2v14H7V7zm4-4h2v18h-2V3zm4 8h2v10h-2V11zm4-6h2v16h-2V5z"/>
                    </svg>
                  </span>
                  Music Analytics
                </h1>
                <p className="dashboard-subtitle">Your personalized music insights</p>
              </div>
              <div className="header-actions">
                <button className="modern-action-btn" onClick={loadPlaylists}>
                  <span className="btn-icon">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18c-.31-.11-.65-.18-1-.18-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3V8h3V6h-5z"/>
                    </svg>
                  </span>
                  Playlists
                </button>
                <button className="modern-close-btn" onClick={() => setShowDashboard(false)}>
                  <span>✕</span>
                </button>
              </div>
            </div>

            {loadingAnalytics ? (
              <div className="modern-loading">
                <div className="loading-animation">
                  <div className="pulse-ring"></div>
                  <div className="pulse-ring delay-1"></div>
                  <div className="pulse-ring delay-2"></div>
                </div>
                <h3>Analyzing your music taste...</h3>
                <p>Gathering insights from your Spotify data</p>
              </div>
            ) : analytics && !analytics.error ? (
              <div className="modern-analytics-layout">
                {/* Stats Overview Cards */}
                <div className="stats-overview">
                  <div 
                    className={`stat-card ${analytics.top_tracks?.[0]?.album_image ? 'album-bg' : ''}`}
                    style={analytics.top_tracks?.[0]?.album_image ? { 
                      backgroundImage: `url(${analytics.top_tracks[0].album_image})` 
                    } : {}}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{analytics.total_tracks || 0}</div>
                      <div className="stat-label">Top Tracks</div>
                    </div>
                  </div>
                  <div 
                    className={`stat-card ${analytics.top_artists?.[0]?.image ? 'album-bg' : ''}`}
                    style={analytics.top_artists?.[0]?.image ? { 
                      backgroundImage: `url(${analytics.top_artists[0].image})` 
                    } : {}}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{analytics.total_artists || 0}</div>
                      <div className="stat-label">Artists</div>
                    </div>
                  </div>
                  <div 
                    className={`stat-card ${analytics.recent_tracks?.[0]?.album_image ? 'album-bg' : ''}`}
                    style={analytics.recent_tracks?.[0]?.album_image ? { 
                      backgroundImage: `url(${analytics.recent_tracks[0].album_image})` 
                    } : {}}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{analytics.recent_tracks?.length || 0}</div>
                      <div className="stat-label">Recent Plays</div>
                    </div>
                  </div>
                  <div 
                    className={`stat-card ${playlists?.playlists?.[0]?.image ? 'album-bg' : ''}`}
                    style={playlists?.playlists?.[0]?.image ? { 
                      backgroundImage: `url(${playlists.playlists[0].image})` 
                    } : {}}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{playlists?.total || 0}</div>
                      <div className="stat-label">Playlists</div>
                    </div>
                  </div>
                </div>

                {/* Main Content Grid */}
                <div className="analytics-main-grid">
                  {/* Top Tracks Section */}
                  <div className="analytics-section top-tracks-section">
                    <div className="section-header">
                      <h3>Your Top Tracks</h3>
                      <span className="section-badge">Most Played</span>
                    </div>
                    <div className="tracks-showcase">
                      {analytics.top_tracks?.slice(0, 5).map((track, index) => (
                        <div 
                          key={track.id} 
                          className={`track-showcase-item ${track.album_image ? 'album-bg' : ''}`}
                          style={track.album_image ? { 
                            backgroundImage: `url(${track.album_image})` 
                          } : {}}
                        >
                          <div className="track-rank">#{index + 1}</div>
                          <div className="track-artwork">
                            <img src={track.album_image} alt={track.name} />
                            <div className="artwork-overlay">
                              <div className="play-indicator">▶</div>
                            </div>
                          </div>
                          <div className="track-info-showcase">
                            <h4 className="track-title">{track.name}</h4>
                            <p className="track-artist">{track.artists?.join(", ")}</p>
                            <div className="popularity-indicator">
                              <div className="popularity-fill" style={{ width: `${track.popularity}%` }}></div>
                              <span className="popularity-text">{track.popularity}% popularity</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Top Artists Section */}
                  <div className="analytics-section artists-section">
                    <div className="section-header">
                      <h3>Favorite Artists</h3>
                      <span className="section-badge">Your Taste</span>
                    </div>
                    <div className="artists-showcase">
                      {analytics.top_artists?.slice(0, 6).map((artist, index) => (
                        <div 
                          key={artist.id} 
                          className={`artist-showcase-item ${artist.image ? 'album-bg' : ''}`}
                          style={artist.image ? { 
                            backgroundImage: `url(${artist.image})` 
                          } : {}}
                        >
                          <div className="artist-image-container">
                            <img src={artist.image} alt={artist.name} className="artist-image" />
                            <div className="artist-rank">#{index + 1}</div>
                          </div>
                          <div className="artist-info">
                            <h4 className="artist-name">{artist.name}</h4>
                            <div className="artist-genres">
                              {artist.genres?.slice(0, 2).map((genre, i) => (
                                <span key={i} className="genre-tag">{genre}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Recent Activity */}
                  <div className="analytics-section recent-section">
                    <div className="section-header">
                      <h3>Recent Activity</h3>
                      <span className="section-badge">Last 24h</span>
                    </div>
                    <div className="recent-activity-list">
                      {analytics.recent_tracks?.slice(0, 8).map((track, index) => (
                        <div key={`${track.id}-${index}`} className="recent-activity-item">
                          <img src={track.album_image} alt={track.name} className="recent-artwork" />
                          <div className="recent-info">
                            <h5 className="recent-track-name">{track.name}</h5>
                            <p className="recent-artist">{track.artists?.join(", ")}</p>
                          </div>
                          <div className="recent-time">
                            {new Date(track.played_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Playlists Section */}
                  {playlists && !playlists.error && (
                    <div className="analytics-section playlists-section">
                      <div className="section-header">
                        <h3>Your Playlists</h3>
                        <span className="section-badge">{playlists.total} Total</span>
                      </div>
                      <div className="playlists-showcase">
                        {playlists.playlists?.slice(0, 6).map((playlist) => (
                          <div key={playlist.id} className="playlist-showcase-item">
                            <div className="playlist-info-card">
                              <h4 className="playlist-name">{playlist.name}</h4>
                              <p className="playlist-meta">
                                {playlist.tracks_count} tracks • {playlist.owner}
                              </p>
                              <div className="playlist-actions">
                                <a
                                  href={playlist.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="playlist-open-btn"
                                >
                                  Open in Spotify
                                </a>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      {playlists.total > 6 && (
                        <div className="playlists-footer">
                          <p>+{playlists.total - 6} more playlists in your library</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="modern-error-state">
                <div className="error-icon">😔</div>
                <h3>Unable to load analytics</h3>
                <p>We couldn't fetch your music data right now</p>
                <button className="retry-btn" onClick={loadAnalytics}>
                  Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Enhanced Profile Dropdown with Close Button */}
      {showProfile && me && (
        <div className="profile-dropdown">
          <div className="profile-header">
            <h3 className="profile-title">Profile Info</h3>
            <button
              className="profile-close-btn"
              onClick={() => setShowProfile(false)}
            >
              ✕
            </button>
          </div>

          <div className="profile-content">
            <p>
              <span>Name:</span>
              <strong>{me.display_name}</strong>
            </p>
            <p>
              <span>Email:</span>
              <strong>{me.email}</strong>
            </p>
            <p>
              <span>Country:</span>
              <strong>{me.country}</strong>
            </p>
            <p>
              <span>Last updated:</span>
              <strong>{lastUpdated}</strong>
            </p>

            <div className="profile-actions">
              <button
                className="profile-action-btn"
                onClick={loadMe}
                disabled={loading}
              >
                {loading ? "Refreshing..." : "🔄 Refresh"}
              </button>
              <button
                className="profile-action-btn secondary"
                onClick={() => setShowRaw(v => !v)}
              >
                {showRaw ? "👁️ Hide Raw" : "👁️ Show Raw"}
              </button>
              <button
                className="profile-action-btn logout-btn"
                onClick={handleLogout}
              >
                🚪 Logout
              </button>
            </div>

            {err && <p className="ghost-error">{err}</p>}

            {showRaw && (
              <pre className="raw-json">
                {JSON.stringify(me, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}