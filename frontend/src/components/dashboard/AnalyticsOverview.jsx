import { useState, useEffect } from "react";

export default function AnalyticsOverview() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      const token = localStorage.getItem("spotifyToken");
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/analytics?token=${token}`);
      
      if (!response.ok) throw new Error("Failed to load analytics");
      
      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      console.error("Analytics error:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <div className="loading-spinner"></div>
        <p>Loading your music analytics...</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="analytics-error">
        <p>Unable to load analytics. Please try again.</p>
        <button onClick={loadAnalytics}>Retry</button>
      </div>
    );
  }

  return (
    <div className="analytics-overview">
      <div className="analytics-header">
        <h2>Your Music Analytics</h2>
        <p>Discover your listening patterns and preferences</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{analytics.stats?.total_tracks || 0}</div>
          <div className="stat-label">Top Tracks</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-number">{analytics.stats?.total_artists || 0}</div>
          <div className="stat-label">Artists</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-number">{analytics.stats?.recent_plays || 0}</div>
          <div className="stat-label">Recent Plays</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-number">16</div>
          <div className="stat-label">Playlists</div>
        </div>
      </div>

      <div className="analytics-content">
        <div className="top-tracks-section">
          <h3>Your Top Tracks</h3>
          <div className="track-list">
            {analytics.top_tracks?.slice(0, 5).map((track, index) => (
              <div key={track.id} className="track-list-item">
                <span className="track-rank">#{index + 1}</span>
                <div className="track-details">
                  <span className="track-name">{track.name}</span>
                  <span className="track-artist">{track.artists.join(", ")}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="top-artists-section">
          <h3>Your Favorite Artists</h3>
          <div className="artist-grid">
            {analytics.top_artists?.slice(0, 6).map((artist) => (
              <div key={artist.id} className="artist-item">
                <div className="artist-image">
                  {artist.image ? (
                    <img src={artist.image} alt={artist.name} />
                  ) : (
                    <div className="artist-placeholder">
                      {artist.name.charAt(0)}
                    </div>
                  )}
                </div>
                <div className="artist-info">
                  <span className="artist-name">{artist.name}</span>
                  <span className="artist-genres">{artist.genres?.slice(0, 2).join(", ")}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
