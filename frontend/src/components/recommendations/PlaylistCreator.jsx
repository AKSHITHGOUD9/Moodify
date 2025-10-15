import { useState } from "react";

export default function PlaylistCreator({ tracks, onClose, onSuccess }) {
  const [playlistName, setPlaylistName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!playlistName.trim()) return;

    try {
      setLoading(true);
      const token = localStorage.getItem("spotifyToken");
      const trackIds = tracks.map(track => track.id);

      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/create-playlist?token=${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: playlistName,
          track_ids: trackIds,
          user_id: "current_user"
        })
      });

      if (!response.ok) throw new Error("Failed to create playlist");

      const result = await response.json();
      alert(`Playlist created successfully!\n\nName: ${result.name}\nTracks: ${result.tracks_added}\n\nCheck your Spotify library!`);
      
      onSuccess();
    } catch (error) {
      console.error("Playlist creation error:", error);
      alert("Failed to create playlist. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="playlist-creator-modal">
      <div className="playlist-creator-content">
        <h3>Create Playlist</h3>
        
        <div className="playlist-form">
          <input
            type="text"
            value={playlistName}
            onChange={(e) => setPlaylistName(e.target.value)}
            placeholder="Enter playlist name"
            className="playlist-name-input"
          />
          
          <div className="selected-tracks">
            <p>Selected tracks ({tracks.length}):</p>
            <ul>
              {tracks.map(track => (
                <li key={track.id}>{track.name} - {track.artists?.map(a => a.name).join(", ")}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="playlist-actions">
          <button 
            className="cancel-btn"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </button>
          <button 
            className="create-btn"
            onClick={handleCreate}
            disabled={loading || !playlistName.trim()}
          >
            {loading ? "Creating..." : "Create Playlist"}
          </button>
        </div>
      </div>
    </div>
  );
}
