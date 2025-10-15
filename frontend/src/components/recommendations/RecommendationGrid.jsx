import { useState } from "react";
import TrackItem from "./TrackItem";
import PlaylistCreator from "./PlaylistCreator";

export default function RecommendationGrid({ recommendations, onPlaylistCreate }) {
  const [selectedTracks, setSelectedTracks] = useState([]);
  const [showPlaylistCreator, setShowPlaylistCreator] = useState(false);

  const handleTrackSelect = (track, isSelected) => {
    if (isSelected) {
      setSelectedTracks(prev => [...prev, track]);
    } else {
      setSelectedTracks(prev => prev.filter(t => t.id !== track.id));
    }
  };

  const handleCreatePlaylist = () => {
    setShowPlaylistCreator(true);
  };

  const handlePlaylistCreated = () => {
    setShowPlaylistCreator(false);
    setSelectedTracks([]);
    onPlaylistCreate();
  };

  return (
    <div className="recommendations-grid">
      <div className="recommendations-header">
        <h3>Your Recommendations</h3>
        {selectedTracks.length > 0 && (
          <button 
            className="create-playlist-btn"
            onClick={handleCreatePlaylist}
          >
            Create Playlist ({selectedTracks.length})
          </button>
        )}
      </div>

      <div className="recommendations-content">
        {recommendations.from_history?.length > 0 && (
          <div className="recommendation-section">
            <h4>From Your History</h4>
            <div className="track-grid">
              {recommendations.from_history.map((track) => (
                <TrackItem
                  key={track.id}
                  track={track}
                  onSelect={handleTrackSelect}
                  isSelected={selectedTracks.some(t => t.id === track.id)}
                />
              ))}
            </div>
          </div>
        )}

        {recommendations.new_discoveries?.length > 0 && (
          <div className="recommendation-section">
            <h4>New Discoveries</h4>
            <div className="track-grid">
              {recommendations.new_discoveries.map((track) => (
                <TrackItem
                  key={track.id}
                  track={track}
                  onSelect={handleTrackSelect}
                  isSelected={selectedTracks.some(t => t.id === track.id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {showPlaylistCreator && (
        <PlaylistCreator
          tracks={selectedTracks}
          onClose={() => setShowPlaylistCreator(false)}
          onSuccess={handlePlaylistCreated}
        />
      )}
    </div>
  );
}
