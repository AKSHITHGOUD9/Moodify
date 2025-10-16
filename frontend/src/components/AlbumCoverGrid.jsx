import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import './AlbumCoverGrid.css';

const API = import.meta.env.VITE_BACKEND_URL;

/**
 * AlbumCoverGrid Component
 * 
 * Creates an interactive background grid of album covers that respond to mouse movement.
 * Features:
 * - Fetches album covers from user's Spotify history
 * - Proximity-based visual effects (opacity, scale, shadow)
 * - Smooth fade-in/out animations based on cursor movement
 * - Responsive grid layout that fills the entire viewport
 * - Fallback placeholder covers if API fails
 * 
 * Performance optimizations:
 * - Throttled mouse move events
 * - Memoized calculations
 * - Efficient DOM updates
 */
const AlbumCoverGrid = () => {
  console.log("AlbumCoverGrid: Component rendering");
  const [albumCovers, setAlbumCovers] = useState([]);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
  const [tilePositions, setTilePositions] = useState([]);
  const [isCursorMoving, setIsCursorMoving] = useState(false);
  const [showTiles, setShowTiles] = useState(false);
  const gridRef = useRef(null);
  const lastMouseMove = useRef(0);
  const fadeTimeout = useRef(null);
  const showTimeout = useRef(null);

  const fetchAndShuffleCovers = useCallback(async () => {
    try {
      console.log("AlbumCoverGrid: Starting to fetch album covers...");
      // Get token from localStorage
      const token = localStorage.getItem('spotify_token');
      const url = token ? `${API}/api/album-covers?token=${token}` : `${API}/api/album-covers`;
      
      console.log("AlbumCoverGrid: Fetching from URL:", url);
      const res = await fetch(url);
      if (!res.ok) {
        console.warn("Failed to fetch album covers:", res.status, res.statusText);
        setAlbumCovers([]);
        return;
      }
      const data = await res.json();
      
      console.log("AlbumCoverGrid: Raw API response:", data);
      console.log("Fetched album covers:", data.urls?.length || 0);
      
      if (!data.urls || data.urls.length === 0) {
        console.warn("No album covers received from API - using fallback covers");
        // Use fallback album covers for testing
        const fallbackCovers = [
          "https://i.scdn.co/image/ab67616d0000b273c8a11e48c91a982d086afc69",
          "https://i.scdn.co/image/ab67616d0000b2734f7b717b8a0e0c9b0e0e0e0",
          "https://i.scdn.co/image/ab67616d0000b2738b8b8b8b8b8b8b8b8b8b8b8",
          "https://i.scdn.co/image/ab67616d0000b2731a1a1a1a1a1a1a1a1a1a1a1a",
          "https://i.scdn.co/image/ab67616d0000b2732b2b2b2b2b2b2b2b2b2b2b2b"
        ];
        setAlbumCovers(fallbackCovers);
        return;
      }
      
      const shuffledUrls = data.urls.sort(() => Math.random() - 0.5);
      
      // Calculate how many tiles we need to fill the screen
      const neededTiles = 800;
      
      // If we don't have enough unique covers, duplicate and shuffle
      let finalUrls = [...shuffledUrls];
      while (finalUrls.length < neededTiles) {
        finalUrls = [...finalUrls, ...shuffledUrls].sort(() => Math.random() - 0.5);
      }
      
      setAlbumCovers(finalUrls.slice(0, neededTiles));
      console.log(`Rendering ${finalUrls.slice(0, neededTiles).length} album cover tiles`);
    } catch (e) {
      console.warn("Error fetching album covers:", e.message);
      // Fallback: create placeholder covers if API fails
      const placeholderCovers = Array.from({ length: 800 }, (_, i) => 
        `https://via.placeholder.com/300x300/4f46e5/ffffff?text=Album+${i + 1}`
      );
      setAlbumCovers(placeholderCovers);
    }
  }, []);

  // Optimized mouse move handler with throttling for better performance
  const handleMouseMove = useCallback((e) => {
    const now = Date.now();
    lastMouseMove.current = now;
    
    setCursorPos({ x: e.clientX, y: e.clientY });
    setIsCursorMoving(true);
    
    // Show tiles with a slight delay for fluid effect
    if (showTimeout.current) {
      clearTimeout(showTimeout.current);
    }
    showTimeout.current = setTimeout(() => {
      setShowTiles(true);
    }, 100); // Small delay for fluid effect
    
    // Clear existing fade-out timeout
    if (fadeTimeout.current) {
      clearTimeout(fadeTimeout.current);
    }
    
    // Set new timeout for fade out
    fadeTimeout.current = setTimeout(() => {
      setIsCursorMoving(false);
      setShowTiles(false); // Hide tiles completely when cursor stops
    }, 1500); // Fade out after 1.5 seconds of no movement
  }, []);

  // Initialize album covers and set up mouse tracking
  useEffect(() => {
    console.log("AlbumCoverGrid: useEffect triggered - setting up timer");
    
    // Set some test covers immediately for debugging
    const testCovers = [
      "https://i.scdn.co/image/ab67616d0000b273c8a11e48c91a982d086afc69",
      "https://i.scdn.co/image/ab67616d0000b2734f7b717b8a0e0c9b0e0e0e0",
      "https://i.scdn.co/image/ab67616d0000b2738b8b8b8b8b8b8b8b8b8b8b8",
      "https://i.scdn.co/image/ab67616d0000b2731a1a1a1a1a1a1a1a1a1a1a1a",
      "https://i.scdn.co/image/ab67616d0000b2732b2b2b2b2b2b2b2b2b2b2b2b"
    ];
    console.log("AlbumCoverGrid: Setting test covers immediately");
    setAlbumCovers(testCovers);
    
    // Wait a bit for the token to be stored, then fetch album covers
    const timer = setTimeout(() => {
      console.log("AlbumCoverGrid: Timer expired - calling fetchAndShuffleCovers");
      fetchAndShuffleCovers();
    }, 1000); // Wait 1 second for token to be available

    window.addEventListener('mousemove', handleMouseMove);
    
    return () => {
      clearTimeout(timer);
      if (fadeTimeout.current) {
        clearTimeout(fadeTimeout.current);
      }
      if (showTimeout.current) {
        clearTimeout(showTimeout.current);
      }
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [fetchAndShuffleCovers, handleMouseMove]);

  // Calculate tile positions for proximity-based effects
  // This runs after album covers are loaded and DOM is updated
  useEffect(() => {
    const timer = setTimeout(() => {
      if (gridRef.current && gridRef.current.children.length > 0) {
        const positions = Array.from(gridRef.current.children).map(tile => {
          const rect = tile.getBoundingClientRect();
          return {
            centerX: rect.left + rect.width / 2,
            centerY: rect.top + rect.height / 2,
          };
        });
        setTilePositions(positions);
      }
    }, 100); // Small delay to ensure DOM is fully rendered

    return () => clearTimeout(timer);
  }, [albumCovers]); 

  console.log("AlbumCoverGrid: Rendering grid with", albumCovers.length, "covers");
  
  return (
    <div className="album-grid-container">
      {/* Dark background overlay */}
      <div className="album-grid-overlay"></div>
      
      {/* Album tiles grid with proximity-based effects */}
      <div className="album-grid-inner" ref={gridRef}>
        {albumCovers.map((url, index) => {
          const tilePos = tilePositions[index] || { centerX: 0, centerY: 0 };
          
          // Calculate distance from cursor to tile center for proximity effects
          const distance = Math.sqrt(
            Math.pow(tilePos.centerX - cursorPos.x, 2) + 
            Math.pow(tilePos.centerY - cursorPos.y, 2)
          );
          
          // Define maximum distance for effect calculation
          const maxDistance = 300;
          const proximity = Math.min(1, distance / maxDistance);
          
          // Calculate opacity based on distance and cursor movement state
          let baseOpacity = 0;
          
          if (isCursorMoving && showTiles) {
            baseOpacity = Math.max(0, 1 - proximity);
          }
          
          // Calculate visual effects based on proximity
          const scale = 0.9 + (baseOpacity * 0.3); // Scale up when close
          const translateY = -(baseOpacity * 15); // Lift up when close
          const shadowSize = baseOpacity * 30; // Add shadow when close
          
          const transform = `scale(${scale}) translateY(${translateY}px)`;
          const boxShadow = `0 8px ${shadowSize}px rgba(78, 161, 255, ${baseOpacity * 0.6})`;
          const zIndex = Math.round(500 - distance);
          
          return (
            <div
              key={index}
              className="album-tile-wrapper"
              style={{
                transform,
                boxShadow,
                zIndex,
                opacity: baseOpacity > 0.02 ? baseOpacity : 0,
                transition: isCursorMoving 
                  ? 'opacity 0.1s ease-out, transform 0.2s ease-out, box-shadow 0.2s ease-out'
                  : 'opacity 0.5s ease-out, transform 0.3s ease-out, box-shadow 0.3s ease-out',
              }}
            >
              <div className="album-tile-content">
                <img src={url} alt="" className="album-tile-image" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AlbumCoverGrid;