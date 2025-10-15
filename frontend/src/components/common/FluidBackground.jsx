import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import './FluidBackground.css';

const API = import.meta.env.VITE_BACKEND_URL;

/**
 * FluidBackground Component (AlbumCoverGrid)
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
const FluidBackground = () => {
  const [albumCovers, setAlbumCovers] = useState([]);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
  const [tilePositions, setTilePositions] = useState([]);
  const [isCursorMoving, setIsCursorMoving] = useState(false);
  const [showTiles, setShowTiles] = useState(false);
  const gridRef = useRef(null);
  const lastMouseMove = useRef(0);
  const fadeTimeout = useRef(null);

  // Fetch album covers from API
  const fetchAlbumCovers = useCallback(async () => {
    try {
      const response = await fetch(`${API}/api/album-covers`);
      if (response.ok) {
        const covers = await response.json();
        if (covers && covers.length > 0) {
          setAlbumCovers(covers);
          setShowTiles(true);
          return;
        }
      }
    } catch (error) {
      console.log('Failed to fetch album covers, using fallback');
    }
    
    // Fallback: Use placeholder covers
    const fallbackCovers = Array.from({ length: 50 }, (_, i) => ({
      id: `fallback-${i}`,
      url: `https://via.placeholder.com/300x300/1a1a1a/666666?text=♪`
    }));
    setAlbumCovers(fallbackCovers);
    setShowTiles(true);
  }, [API]);

  // Calculate grid positions
  const calculateTilePositions = useCallback(() => {
    if (!gridRef.current || albumCovers.length === 0) return;

    const container = gridRef.current;
    const rect = container.getBoundingClientRect();
    const tiles = container.querySelectorAll('.album-tile');
    
    const positions = Array.from(tiles).map(tile => {
      const tileRect = tile.getBoundingClientRect();
      return {
        x: tileRect.left + tileRect.width / 2,
        y: tileRect.top + tileRect.height / 2,
        width: tileRect.width,
        height: tileRect.height
      };
    });
    
    setTilePositions(positions);
  }, [albumCovers]);

  // Handle mouse movement with throttling
  const handleMouseMove = useCallback((e) => {
    const now = Date.now();
    if (now - lastMouseMove.current < 16) return; // ~60fps throttling
    lastMouseMove.current = now;

    setCursorPos({ x: e.clientX, y: e.clientY });
    setIsCursorMoving(true);

    // Clear existing timeout
    if (fadeTimeout.current) {
      clearTimeout(fadeTimeout.current);
    }

    // Set fade timeout
    fadeTimeout.current = setTimeout(() => {
      setIsCursorMoving(false);
    }, 150);
  }, []);

  // Calculate proximity effects for each tile
  const getTileStyle = useCallback((index) => {
    if (!isCursorMoving || tilePositions.length === 0) {
      return {
        opacity: 0.1,
        transform: 'scale(1)',
        filter: 'blur(0px)',
        boxShadow: 'none'
      };
    }

    const tile = tilePositions[index];
    if (!tile) return { opacity: 0.1 };

    const distance = Math.sqrt(
      Math.pow(cursorPos.x - tile.x, 2) + Math.pow(cursorPos.y - tile.y, 2)
    );

    const maxDistance = 200;
    const normalizedDistance = Math.min(distance / maxDistance, 1);
    const proximity = 1 - normalizedDistance;

    const opacity = Math.max(0.1, 0.3 + proximity * 0.7);
    const scale = 1 + proximity * 0.2;
    const blur = Math.max(0, (1 - proximity) * 3);
    const shadowIntensity = proximity * 20;

    return {
      opacity,
      transform: `scale(${scale})`,
      filter: `blur(${blur}px)`,
      boxShadow: `0 0 ${shadowIntensity}px rgba(29, 185, 84, ${proximity * 0.5})`,
      transition: 'all 0.1s ease-out'
    };
  }, [cursorPos, tilePositions, isCursorMoving]);

  // Initialize
  useEffect(() => {
    fetchAlbumCovers();
  }, [fetchAlbumCovers]);

  useEffect(() => {
    if (albumCovers.length > 0) {
      // Small delay to ensure DOM is ready
      setTimeout(calculateTilePositions, 100);
    }
  }, [albumCovers, calculateTilePositions]);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', calculateTilePositions);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', calculateTilePositions);
      if (fadeTimeout.current) {
        clearTimeout(fadeTimeout.current);
      }
    };
  }, [handleMouseMove, calculateTilePositions]);

  if (!showTiles || albumCovers.length === 0) {
    return null;
  }

  return (
    <div className="album-grid-container">
      <div className="album-grid-overlay"></div>
      <div className="album-grid-inner" ref={gridRef}>
        {albumCovers.map((cover, index) => (
          <div
            key={cover.id}
            className="album-tile"
            style={getTileStyle(index)}
          >
            <img
              src={cover.url}
              alt="Album cover"
              className="album-image"
              loading="lazy"
              onError={(e) => {
                e.target.src = 'https://via.placeholder.com/300x300/1a1a1a/666666?text=♪';
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default FluidBackground;
