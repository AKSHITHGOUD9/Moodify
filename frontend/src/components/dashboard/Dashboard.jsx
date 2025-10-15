import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import SearchBar from "../recommendations/SearchBar";
import RecommendationGrid from "../recommendations/RecommendationGrid";
import AnalyticsOverview from "./AnalyticsOverview";
import ChartsModal from "../charts/ChartsModal";
import ProfileDropdown from "../auth/ProfileDropdown";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showCharts, setShowCharts] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const handleSearch = async (query) => {
    try {
      setLoading(true);
      const token = localStorage.getItem("spotifyToken");
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/recommend-v2?token=${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      
      if (!response.ok) throw new Error("Failed to get recommendations");
      
      const data = await response.json();
      setRecommendations(data);
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <h1>Moodify</h1>
          <span className="user-greeting">Welcome back, {user?.display_name}</span>
        </div>
        
        <div className="header-right">
          <button 
            className="charts-btn"
            onClick={() => setShowCharts(true)}
          >
            Charts
          </button>
          
          <button 
            className="profile-btn"
            onClick={() => setShowProfile(!showProfile)}
          >
            {user?.images?.[0]?.url ? (
              <img 
                src={user.images[0].url} 
                alt="Profile" 
                className="profile-avatar"
              />
            ) : (
              <span className="profile-initial">
                {user?.display_name?.charAt(0) || "U"}
              </span>
            )}
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="search-section">
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>

        {recommendations && (
          <div className="recommendations-section">
            <RecommendationGrid 
              recommendations={recommendations}
              onPlaylistCreate={() => setRecommendations(null)}
            />
          </div>
        )}

        {!recommendations && (
          <div className="analytics-section">
            <AnalyticsOverview />
          </div>
        )}
      </main>

      {showCharts && (
        <ChartsModal onClose={() => setShowCharts(false)} />
      )}

      {showProfile && (
        <ProfileDropdown 
          user={user}
          onClose={() => setShowProfile(false)}
          onLogout={logout}
        />
      )}
    </div>
  );
}
