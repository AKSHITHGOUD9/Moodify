export default function ChartsModal({ onClose }) {
  return (
    <div className="charts-modal-overlay" onClick={onClose}>
      <div className="charts-modal" onClick={(e) => e.stopPropagation()}>
        <div className="charts-header">
          <h2>Music Analytics Charts</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="charts-content">
          <div className="chart-placeholder">
            <h3>📊 Listening Trends</h3>
            <p>Your music listening patterns over time</p>
            <div className="chart-mock">Chart visualization coming soon...</div>
          </div>
          
          <div className="chart-placeholder">
            <h3>🎵 Genre Distribution</h3>
            <p>Your favorite music genres</p>
            <div className="chart-mock">Chart visualization coming soon...</div>
          </div>
          
          <div className="chart-placeholder">
            <h3>🎤 Artist Popularity</h3>
            <p>Your most played artists</p>
            <div className="chart-mock">Chart visualization coming soon...</div>
          </div>
        </div>
      </div>
    </div>
  );
}
