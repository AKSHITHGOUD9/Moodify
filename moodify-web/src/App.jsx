import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import "./App.css";

import AlbumCoverGrid from "./components/AlbumCoverGrid";
import RecommendationGridV2 from "./components/RecommendationGridV2";
import ChartsModal from "./components/ChartsModal";

// =============================================================================
// CONFIGURATION
// =============================================================================

const API = import.meta.env.VITE_BACKEND_URL || "https://moodify-ai-powered.onrender.com";
const ELEGANT_QUOTE = "Your emotions, our algorithms, pure magic";

// =============================================================================
// MAIN APP COMPONENT
// =============================================================================

export default function App() {

  // =============================================================================
  // STATE MANAGEMENT
  // =============================================================================
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
  const [showProfile, setShowProfile] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showHowItWorks, setShowHowItWorks] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [playlists, setPlaylists] = useState(null);
  const [loadingPlaylists, setLoadingPlaylists] = useState(false);
  const [createPlaylist, setCreatePlaylist] = useState(false);
  const [playlistName, setPlaylistName] = useState("");
  const [activeTab, setActiveTab] = useState("charts");
  const [showTooltip, setShowTooltip] = useState(null);
  const [showChartsModal, setShowChartsModal] = useState(false);
  const [recommendationData, setRecommendationData] = useState(null);
  const [spotifyToken, setSpotifyToken] = useState(null);
  const recommendationRef = useRef(null);

  // =============================================================================
  // DATA FETCHING & AUTHENTICATION
  // =============================================================================
  
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const userId = urlParams.get('user_id');
    
    if (token) {
      setSpotifyToken(token);
      localStorage.setItem('spotify_token', token);
      if (userId) {
        localStorage.setItem('spotify_user_id', userId);
      }
      
      setRecsErr("");
      window.history.replaceState({}, document.title, window.location.pathname);
      fetchUserDataWithToken(token);
    } else {
      const storedToken = localStorage.getItem('spotify_token');
      if (storedToken) {
        setSpotifyToken(storedToken);
        setRecsErr("");
        fetchUserDataWithToken(storedToken);
      }
    }
  }, []);

  const fetchUserDataWithToken = async (token) => {
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
    const timestamp = Date.now();
    window.location.href = `${API}/login?t=${timestamp}`;
  }, []);

  const loadMe = useCallback(async () => {
    if (spotifyToken) {
      return fetchUserDataWithToken(spotifyToken);
    }
    return;
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await fetch(`${API}/logout`, { 
        method: "POST", 
        credentials: "include" 
      });
      
      setMe(null);
      setShowProfile(false);
      setRecs([]);
      setTrackIds([]);
      setAnalytics(null);
      setPlaylists(null);
      setRecommendationData(null);
      setErr("");
      setSpotifyToken(null);
      
      localStorage.removeItem('spotify_token');
      localStorage.removeItem('spotify_user_id');
      
      alert("Successfully logged out!");
    } catch (e) {
      console.error("Error during logout:", e);
      alert("Error during logout. Please try again.");
    }
  }, []);

  // =============================================================================
  // ANALYTICS & DATA LOADING
  // =============================================================================

  const loadAnalytics = useCallback(async () => {
    setLoadingAnalytics(true);
    try {
      const url = spotifyToken ? `${API}/api/top-tracks?token=${spotifyToken}` : `${API}/api/top-tracks`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAnalytics(data);
    } catch (e) {
      console.error("Failed to load analytics:", e);
      setAnalytics({ error: "Failed to load analytics data" });
    } finally {
      setLoadingAnalytics(false);
    }
  }, [spotifyToken]);

  const loadPlaylists = useCallback(async () => {
    setLoadingPlaylists(true);
    try {
      const url = spotifyToken ? `${API}/api/my-playlists?token=${spotifyToken}` : `${API}/api/my-playlists`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPlaylists(data);
    } catch (e) {
      console.error("Failed to load playlists:", e);
      setPlaylists({ error: "Failed to load playlists" });
    } finally {
      setLoadingPlaylists(false);
    }
  }, [spotifyToken]);


  const toggleDashboard = useCallback(() => {
    if (!showDashboard) {
      if (!analytics) {
        loadAnalytics();
      }
      if (!playlists) {
        loadPlaylists();
      }
    }
    setShowDashboard(!showDashboard);
  }, [showDashboard, analytics, playlists, loadAnalytics, loadPlaylists]);

  // =============================================================================
  // RECOMMENDATIONS
  // =============================================================================

  const generateRecs = useCallback(async () => {
    if (!mood.trim()) return;
    
    if (!spotifyToken) {
      setRecsErr("Please wait for authentication to complete");
      setIsGenerating(false);
      return;
    }

    setIsGenerating(true);
    setRecsErr("");
    setRecs([]);
    setTrackIds([]);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);
      
      const url = spotifyToken ? `${API}/recommend-v2?token=${spotifyToken}` : `${API}/recommend-v2`;
      
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          query: mood.trim(),
          create_playlist: false,
        }),
      });
      
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      setRecs(data);
      
      if (data.tracks?.length > 0) {
        const ids = data.tracks.map(track => track.id);
        setTrackIds(ids);
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

  const tracksToUse = useMemo(() => {
    if (recommendationData) {
      return recommendationData.getSelectedTrackIds ? recommendationData.getSelectedTrackIds() : [];
    }
    return trackIds;
  }, [recommendationData, trackIds]);

  // =============================================================================
  // PLAYLIST CREATION
  // =============================================================================

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
      
      // Get token from localStorage
      const token = localStorage.getItem('spotify_token');
      const url = token ? `${API}/create-playlist?token=${token}` : `${API}/create-playlist`;
      
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(playlistData),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      alert(`Playlist created successfully!\n\nName: ${data.playlist.name}\nTracks: ${data.playlist.tracks_added}\n\nCheck your Spotify library!`);
      
    } catch (e) {
      console.error("Failed to create playlist:", e);
      alert("Failed to create playlist. Please try again.");
    }
  };

  const handleRecommendationsGenerated = (data) => {
    setRecommendationData(data);
  };

  // =============================================================================
  // UI EVENT HANDLERS
  // =============================================================================

  const handleSearchInputChange = useCallback((e) => {
    const value = e.target.value;
    setMood(value);
    setIsTyping(value.trim().length > 0);
    
    // Clear recommendations when search is cleared
    if (value.trim().length === 0) {
      setRecs([]);
      setTrackIds([]);
      setRecommendationData(null);
    }
  }, []);


  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && mood.trim() && !isGenerating) {
      setIsTyping(false); // Clear typing state when searching
      // Trigger RecommendationGridV2 to generate recommendations
      if (recommendationRef.current) {
        recommendationRef.current.triggerGeneration();
      }
    }
  }, [mood, isGenerating]);

  // =============================================================================
  // UI EFFECTS
  // =============================================================================

  useEffect(() => {
    if (!spotifyToken) {
      return;
    }
  }, [spotifyToken]);

  // =============================================================================
  // RENDER
  // =============================================================================
  
  return (
    <div className="app-container">
      {/* Advanced Fluid Cursor Animation - Only show when user is authenticated */}
      {me && <AlbumCoverGrid />}

      {/* Main content */}
      <div className="content">
        {/* Ultra Transparent Header */}
        <header className="ultra-transparent-header">
          <div className="transparent-logo">
            <span className="logo-gradient">Moodify</span>
          </div>

          {me && (
            <div className="transparent-nav">
              <button className="ghost-btn" onClick={() => setShowHowItWorks(true)}>
                How it Works
              </button>
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
              {/* Server Disclaimer */}
              <div className="server-disclaimer">
                <div className="disclaimer-content">
                  <div className="disclaimer-icon">⚡</div>
                  <div className="disclaimer-text">
                    <strong>Server Notice:</strong> This app is currently hosted on Render's free tier and might take a moment to start up. Please bear with us as we scale up in the future!
                  </div>
                </div>
              </div>

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
                  <h2 className="main-title">What's Your Vibe?</h2>
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
                      onClick={isGenerating ? () => setIsGenerating(false) : (() => {
                        setIsTyping(false);
                        // Trigger RecommendationGridV2 to generate recommendations
                        if (recommendationRef.current) {
                          recommendationRef.current.triggerGeneration();
                        }
                      })}
                      disabled={!mood.trim()}
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

                  {/* Toggle removed - now always using AI system */}
                </div>

                {recsErr && <p className="ghost-error">{recsErr}</p>}
              </section>

              {/* Recommendations section */}
              {mood.trim() && (
                <section className="recommendations-section">
                  <RecommendationGridV2 
                    ref={recommendationRef}
                    query={mood} 
                    onRecommendationsGenerated={handleRecommendationsGenerated}
                  />

                  {/* Playlist Creation Button */}
                  <div style={{ textAlign: "center", margin: "2rem auto" }}>
                    <button
                      className="login-button" 
                      onClick={createPlaylistFromRecs}
                      disabled={isGenerating || !recommendationData?.getSelectedTrackIds?.()?.length}
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
                <button className="modern-action-btn" onClick={() => setShowChartsModal(true)}>
                  <span className="btn-icon">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M3 13h2v8H3v-8zm4-6h2v14H7V7zm4-4h2v18h-2V3zm4 8h2v10h-2V11zm4-6h2v16h-2V5z"/>
                    </svg>
                  </span>
                  Charts
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
                    className={`stat-card click-card ${analytics.top_tracks?.[0]?.album_image ? 'album-bg' : ''}`}
                    style={analytics.top_tracks?.[0]?.album_image ? { 
                      backgroundImage: `url(${analytics.top_tracks[0].album_image})` 
                    } : {}}
                    onClick={() => setShowTooltip(showTooltip === 'tracks' ? null : 'tracks')}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{analytics.total_tracks || 0}</div>
                      <div className="stat-label">Top Tracks</div>
                    </div>
                  </div>
                  <div 
                    className={`stat-card click-card ${analytics.top_artists?.[0]?.image ? 'album-bg' : ''}`}
                    style={analytics.top_artists?.[0]?.image ? { 
                      backgroundImage: `url(${analytics.top_artists[0].image})` 
                    } : {}}
                    onClick={() => setShowTooltip(showTooltip === 'artists' ? null : 'artists')}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{analytics.total_artists || 0}</div>
                      <div className="stat-label">Artists</div>
                    </div>
                  </div>
                  <div 
                    className={`stat-card click-card ${analytics.recent_tracks?.[0]?.album_image ? 'album-bg' : ''}`}
                    style={analytics.recent_tracks?.[0]?.album_image ? { 
                      backgroundImage: `url(${analytics.recent_tracks[0].album_image})` 
                    } : {}}
                    onClick={() => setShowTooltip(showTooltip === 'recent' ? null : 'recent')}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{analytics.recent_tracks?.length || 0}</div>
                      <div className="stat-label">Recent Plays</div>
                    </div>
                  </div>
                  <div 
                    className={`stat-card click-card ${playlists?.playlists?.[0]?.image ? 'album-bg' : ''}`}
                    style={playlists?.playlists?.[0]?.image ? { 
                      backgroundImage: `url(${playlists.playlists[0].image})` 
                    } : {}}
                    onClick={() => setShowTooltip(showTooltip === 'playlists' ? null : 'playlists')}
                  >
                    <div className="stat-content">
                      <div className="stat-number">{playlists?.total || 0}</div>
                      <div className="stat-label">Playlists</div>
                    </div>
                  </div>
                </div>

                {/* Click-to-Show Lists Modal */}
                {showTooltip && (
                  <div className="click-list-modal">
                    <div className="click-list-content">
                      <button className="close-list-btn" onClick={() => setShowTooltip(null)}>✕</button>
                      
                      {showTooltip === 'tracks' && (
                        <div>
                          <h3>Your Top Tracks</h3>
                          <div className="click-list">
                            {analytics.top_tracks?.slice(0, 10).map((track, index) => (
                              <div key={track.id} className="click-list-item">
                                <img src={track.album_image} alt={track.name} className="click-list-image" />
                                <div className="click-list-info">
                                  <div className="click-list-title">{track.name}</div>
                                  <div className="click-list-subtitle">{track.artists?.join(", ")}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {showTooltip === 'artists' && (
                        <div>
                          <h3>Your Favorite Artists</h3>
                          <div className="click-list">
                            {analytics.top_artists?.slice(0, 10).map((artist, index) => (
                              <div key={artist.id} className="click-list-item">
                                <img src={artist.image} alt={artist.name} className="click-list-image" />
                                <div className="click-list-info">
                                  <div className="click-list-title">{artist.name}</div>
                                  <div className="click-list-subtitle">{artist.genres?.slice(0, 2).join(", ")}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {showTooltip === 'recent' && (
                        <div>
                          <h3>Recent Activity</h3>
                          <div className="click-list">
                            {analytics.recent_tracks?.slice(0, 10).map((track, index) => (
                              <div key={`${track.id}-${index}`} className="click-list-item">
                                <img src={track.album_image} alt={track.name} className="click-list-image" />
                                <div className="click-list-info">
                                  <div className="click-list-title">{track.name}</div>
                                  <div className="click-list-subtitle">{track.artists?.join(", ")}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {showTooltip === 'playlists' && (
                        <div>
                          <h3>Your Playlists</h3>
                          <div className="click-list">
                            {playlists?.playlists?.slice(0, 10).map((playlist) => (
                              <div key={playlist.id} className="click-list-item">
                                <div className="click-list-image playlist-icon">📁</div>
                                <div className="click-list-info">
                                  <div className="click-list-title">{playlist.name}</div>
                                  <div className="click-list-subtitle">{playlist.tracks_count} tracks</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

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
                          className={`track-showcase-item no-hover ${track.album_image ? 'album-bg' : ''}`}
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
                          className={`artist-showcase-item no-hover ${artist.image ? 'album-bg' : ''}`}
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

      {/* Charts Modal */}
      <ChartsModal 
        isOpen={showChartsModal} 
        onClose={() => setShowChartsModal(false)} 
        analytics={analytics} 
      />

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
                onClick={() => spotifyToken ? fetchUserDataWithToken(spotifyToken) : null}
                disabled={loading}
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>
              <button
                className="profile-action-btn secondary"
                onClick={() => setShowRaw(v => !v)}
              >
                {showRaw ? "Hide Raw" : "Show Raw"}
              </button>
              <button
                className="profile-action-btn logout-btn"
                onClick={handleLogout}
              >
                Logout
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

      {/* How it Works Modal */}
      {showHowItWorks && (
        <div className="how-it-works-overlay">
          <div className="how-it-works-container">
            <div className="how-it-works-header">
              <h2>How Moodify Works</h2>
              <button 
                className="close-btn" 
                onClick={() => setShowHowItWorks(false)}
              >
                ×
              </button>
            </div>
            <div className="how-it-works-content">
              <div className="step">
                <div className="step-number">1</div>
                <div className="step-content">
                  <h3>Moodify Analyze Your Music</h3>
                  <p>When you connect Spotify, we analyze your listening history to understand your musical taste - your favorite artists, genres, and regional preferences.</p>
                </div>
              </div>
              
              <div className="step">
                <div className="step-number">2</div>
                <div className="step-content">
                  <h3>AI Creates Your Profile</h3>
                  <p>Our AI builds a personalized music profile based on your Spotify data, learning what you love to listen to.</p>
                </div>
              </div>
              
              <div className="step">
                <div className="step-number">3</div>
                <div className="step-content">
                  <h3>Smart Search & Recommendations</h3>
                  <p>When you search for "chill old Telugu songs," our AI uses your profile to find specific songs you'll actually love, not just generic suggestions.</p>
                </div>
              </div>
              
              <div className="step">
                <div className="step-number">4</div>
                <div className="step-content">
                  <h3>Personalized Results</h3>
                  <p>Get recommendations from your history and discover new songs that match your unique taste - all powered by AI, not just algorithms.</p>
                </div>
              </div>
            </div>
            <div className="how-it-works-footer">
              <p><strong>Simple, Smart, Personal.</strong> That's Moodify.</p>
              <button 
                className="got-it-btn" 
                onClick={() => setShowHowItWorks(false)}
              >
                Got it!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}