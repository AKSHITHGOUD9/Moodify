export default function TrackItem({ track, onSelect, isSelected }) {
  const handleSelect = () => {
    onSelect(track, !isSelected);
  };

  const handlePlay = () => {
    if (track.external_urls?.spotify) {
      window.open(track.external_urls.spotify, "_blank");
    }
  };

  return (
    <div className={`track-item ${isSelected ? "selected" : ""}`}>
      <div className="track-image-container">
        {track.album_image ? (
          <img 
            src={track.album_image} 
            alt={track.name}
            className="track-image"
          />
        ) : (
          <div className="track-placeholder">
            <span>♪</span>
          </div>
        )}
        
        <div className="track-overlay">
          <button 
            className="play-btn"
            onClick={handlePlay}
            title="Play on Spotify"
          >
            ▶
          </button>
        </div>
      </div>

      <div className="track-info">
        <h4 className="track-name" title={track.name}>
          {track.name}
        </h4>
        <p className="track-artists">
          {track.artists?.map(artist => artist.name).join(", ")}
        </p>
        {track.album?.name && (
          <p className="track-album">{track.album.name}</p>
        )}
      </div>

      <button 
        className={`select-btn ${isSelected ? "selected" : ""}`}
        onClick={handleSelect}
      >
        {isSelected ? "✓" : "+"}
      </button>
    </div>
  );
}
