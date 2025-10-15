import { useState } from "react";

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSubmit(e);
    }
  };

  return (
    <div className="search-container">
      <div className="search-header">
        <h2>What's Your Vibe?</h2>
        <p className="search-subtitle">Your emotions, our algorithms, pure magic</p>
      </div>

      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-input-container">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Try 'chill old Telugu songs' or 'energetic workout music'"
            className="search-input"
            disabled={loading}
          />
          <button 
            type="submit" 
            className="search-btn"
            disabled={loading || !query.trim()}
          >
            {loading ? "Searching..." : "Go"}
          </button>
        </div>
      </form>

      <div className="search-suggestions">
        <p>Popular searches:</p>
        <div className="suggestion-tags">
          {["chill songs", "workout music", "old hits", "new releases", "romantic songs"].map((suggestion) => (
            <button
              key={suggestion}
              className="suggestion-tag"
              onClick={() => setQuery(suggestion)}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
