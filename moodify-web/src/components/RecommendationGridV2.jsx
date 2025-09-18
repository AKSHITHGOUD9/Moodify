import { useState, useEffect } from 'react';
// import SpotifyPlayer from './SpotifyPlayer'; // Removed for now
import './RecommendationGridV2.css';

const API = import.meta.env.VITE_BACKEND_URL;

const RecommendationGridV2 = ({ query, onRecommendationsGenerated }) => {
  const [historyRecs, setHistoryRecs] = useState([]);
  const [newRecs, setNewRecs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [hasGenerated, setHasGenerated] = useState(false);
  // const [currentTrack, setCurrentTrack] = useState(null);
  // const [isPlaying, setIsPlaying] = useState(false);
  // const [playingTrackId, setPlayingTrackId] = useState(null);

  const generateRecommendations = async () => {
    if (!query.trim() || hasGenerated) return;

    setLoading(true);
    setError('');
    setHasGenerated(true);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
      
      const response = await fetch(`${API}/recommend-v2`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ query: query.trim() }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      
      setHistoryRecs(data.user_history_recs || []);
      setNewRecs(data.new_recs || []);
      setAnalysis(data.analysis);
      
      // Notify parent component
      if (onRecommendationsGenerated) {
        onRecommendationsGenerated({
          history: data.user_history_recs || [],
          new: data.new_recs || [],
          analysis: data.analysis
        });
      }
      
    } catch (err) {
      console.error('Error generating recommendations:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Reset when query changes
  useEffect(() => {
    setHasGenerated(false);
    setHistoryRecs([]);
    setNewRecs([]);
    setError('');
    setAnalysis(null);
  }, [query]);

  // Debounced generation - only generate after user stops typing for 1 second
  useEffect(() => {
    if (!query.trim()) return;
    
    const timeoutId = setTimeout(() => {
      if (query.trim() && !hasGenerated) {
        generateRecommendations();
      }
    }, 1000); // Wait 1 second after user stops typing

    return () => clearTimeout(timeoutId);
  }, [query]); // Only depend on query, not hasGenerated

  const handleTrackToggle = (trackId, source) => {
    if (source === 'history') {
      setHistoryRecs(prev => 
        prev.map(track => 
          track.id === trackId 
            ? { ...track, selected: !track.selected }
            : track
        )
      );
    } else {
      setNewRecs(prev => 
        prev.map(track => 
          track.id === trackId 
            ? { ...track, selected: !track.selected }
            : track
        )
      );
    }
  };

  const handleTrackReorder = (source, fromIndex, toIndex) => {
    if (source === 'history') {
      setHistoryRecs(prev => {
        const newList = [...prev];
        const [removed] = newList.splice(fromIndex, 1);
        newList.splice(toIndex, 0, removed);
        return newList;
      });
    } else {
      setNewRecs(prev => {
        const newList = [...prev];
        const [removed] = newList.splice(fromIndex, 1);
        newList.splice(toIndex, 0, removed);
        return newList;
      });
    }
  };

  const getAllSelectedTracks = () => {
    const selectedHistory = historyRecs.filter(track => track.selected);
    const selectedNew = newRecs.filter(track => track.selected);
    return [...selectedHistory, ...selectedNew];
  };

  const getSelectedTrackIds = () => {
    return getAllSelectedTracks().map(track => track.id);
  };

  // const handleTrackPlay = (track) => {
  //   setCurrentTrack(track);
  //   setPlayingTrackId(track.id);
  //   // The SpotifyPlayer component will handle the actual playback
  // };

  // const handlePlayPause = (playing) => {
  //   setIsPlaying(playing);
  // };

  // Expose methods to parent component
  useEffect(() => {
    if (onRecommendationsGenerated) {
      onRecommendationsGenerated({
        history: historyRecs,
        new: newRecs,
        analysis,
        getAllSelectedTracks,
        getSelectedTrackIds,
        handleTrackToggle,
        handleTrackReorder
      });
    }
  }, [historyRecs, newRecs, analysis]);

  if (loading) {
    return (
      <div className="recommendation-loading">
        <div className="loading-spinner">
          <div className="spinner-ring"></div>
        </div>
        <h3>AI is analyzing your music taste...</h3>
        <p>Selecting songs from your history and generating new recommendations</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendation-error">
        <div className="error-icon">😔</div>
        <h3>Failed to generate recommendations</h3>
        <p>{error}</p>
        <button onClick={generateRecommendations} className="retry-btn">
          Try Again
        </button>
      </div>
    );
  }

  if (!historyRecs.length && !newRecs.length) {
    return null;
  }

  return (
    <div className="fused-recommendation-container">
      {/* Playlist Info Section */}
      <div className="playlist-info">
        <div className="playlist-left">
          <div className="album-collage">
            {[...historyRecs.slice(0, 2), ...newRecs.slice(0, 2)].map((track, index) => (
              <div key={`${track.id}-${index}`} className="album-tile">
                <img 
                  src={track.album_image || (track.images && track.images[0]?.url) || '/placeholder-album.png'} 
                  alt={track.album}
                  className="album-image"
                />
              </div>
            ))}
          </div>
        </div>
        
        <div className="playlist-right">
          <h2 className="playlist-title">Moodify Recommendations</h2>
          <p className="playlist-creator">Created by Moodify AI</p>
          <div className="playlist-status">
            <span className="saved-indicator">✓ Saved on Spotify</span>
          </div>
          <div className="playlist-hint">
            <span className="hint-text">💡 Drag to reorder • Click to select/deselect</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="recommendation-columns">
        {/* History Recommendations Column */}
        <div className="recommendation-column history-column">
          <div className="column-header">
            <h4>🎵 From Your History</h4>
            <span className="track-count">{historyRecs.length} songs</span>
          </div>
          <div className="track-list">
            {historyRecs.map((track, index) => (
              <TrackItem
                key={track.id}
                track={track}
                index={index}
                source="history"
                onToggle={handleTrackToggle}
                onReorder={handleTrackReorder}
              />
            ))}
          </div>
        </div>

        {/* New Recommendations Column */}
        <div className="recommendation-column new-column">
          <div className="column-header">
            <h4>✨ New Discoveries</h4>
            <span className="track-count">{newRecs.length} songs</span>
          </div>
          <div className="track-list">
            {newRecs.map((track, index) => (
              <TrackItem
                key={track.id}
                track={track}
                index={index}
                source="new"
                onToggle={handleTrackToggle}
                onReorder={handleTrackReorder}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="embed-footer">
        <p>You can delete this playlist in the Web player (opens in a new tab), or from your Spotify app</p>
        <p className="product-label">Product: Embeds</p>
      </div>
    </div>
  );
};

const TrackItem = ({ track, index, source, onToggle, onReorder }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragStart = (e) => {
    setIsDragging(true);
    e.dataTransfer.setData('text/plain', JSON.stringify({ index, source }));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    
    if (data.source === source && data.index !== index) {
      onReorder(source, data.index, index);
    }
  };

  const formatDuration = (ms) => {
    if (!ms) return '0:00';
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className={`fused-track-item ${track.selected ? 'selected' : ''} ${isDragging ? 'dragging' : ''}`}
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div className="track-number">
        {index + 1}
      </div>
      
      <div className="track-main-info">
        <div className="track-image">
          {track.album_image ? (
            <img src={track.album_image} alt={track.name} />
          ) : track.images && track.images[0] ? (
            <img src={track.images[0].url} alt={track.name} />
          ) : (
            <div className="image-placeholder">🎵</div>
          )}
        </div>
        
        <div className="track-details">
          <div className="track-name">{track.name}</div>
          <div className="track-artist">{track.artists?.join(', ')}</div>
          <div className="track-album">{track.album}</div>
          
          {/* Confidence Score for History Tracks */}
          {source === 'history' && track.match_score !== undefined && (
            <div className="confidence-score">
              <span className="confidence-label">Match:</span>
              <div className="confidence-bar">
                <div 
                  className="confidence-fill" 
                  style={{ width: `${Math.min((track.match_score / 10) * 100, 100)}%` }}
                ></div>
              </div>
              <span className="confidence-text">{track.match_score}/10</span>
            </div>
          )}
          
          {/* Popularity for New Tracks */}
          {source === 'new' && track.popularity && (
            <div className="track-popularity">
              <span className="popularity-label">Popularity:</span>
              <div className="popularity-bar">
                <div 
                  className="popularity-fill" 
                  style={{ width: `${track.popularity}%` }}
                ></div>
              </div>
              <span className="popularity-text">{track.popularity}%</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="track-actions">
        <button 
          className="select-button"
          onClick={() => onToggle(track.id, source)}
          title={track.selected ? "Deselect" : "Select"}
        >
          {track.selected ? "✓" : "○"}
        </button>
      </div>
      
      <div className="track-duration">
        {formatDuration(track.duration_ms || 0)}
      </div>
    </div>
  );
};

export default RecommendationGridV2;
