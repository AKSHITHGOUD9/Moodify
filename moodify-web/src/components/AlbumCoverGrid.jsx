import { useEffect, useState, useRef } from 'react';
import './AlbumCoverGrid.css';

const API = import.meta.env.VITE_BACKEND_URL;

const AlbumCoverGrid = () => {
  const [albumCovers, setAlbumCovers] = useState([]);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
  const [tilePositions, setTilePositions] = useState([]);
  const [isCursorMoving, setIsCursorMoving] = useState(false);
  const [showTiles, setShowTiles] = useState(false);
  const gridRef = useRef(null);
  const lastMouseMove = useRef(0);
  const fadeTimeout = useRef(null);
  const showTimeout = useRef(null);

  const fetchAndShuffleCovers = async () => {
    try {
      const res = await fetch(`${API}/api/album-covers`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch album covers");
      const data = await res.json();
      
      console.log("Fetched album covers:", data.urls?.length || 0);
      
      if (!data.urls || data.urls.length === 0) {
        console.warn("No album covers received from API");
        setAlbumCovers([]);
        return;
      }
      
      const shuffledUrls = data.urls.sort(() => Math.random() - 0.5);
      
      // Calculate how many tiles we need to fill the screen
      // With 100px tiles and 20px gaps, we need more tiles for full coverage
      const neededTiles = 1200; // Increased for better coverage
      
      // If we don't have enough unique covers, duplicate and shuffle
      let finalUrls = [...shuffledUrls];
      while (finalUrls.length < neededTiles) {
        finalUrls = [...finalUrls, ...shuffledUrls].sort(() => Math.random() - 0.5);
      }
      
      setAlbumCovers(finalUrls.slice(0, neededTiles));
      console.log(`Rendering ${finalUrls.slice(0, neededTiles).length} album cover tiles`);
    } catch (e) {
      console.error("Error fetching album covers:", e);
      // Fallback: create placeholder covers if API fails
      const placeholderCovers = Array.from({ length: 1200 }, (_, i) => 
        `https://via.placeholder.com/300x300/4f46e5/ffffff?text=Album+${i + 1}`
      );
      setAlbumCovers(placeholderCovers);
    }
  };

  useEffect(() => {
    fetchAndShuffleCovers(); // Initial load only - no shuffling

    const handleMouseMove = (e) => {
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
      }, 0.5); // Small delay for fluid effect
      
      // Clear existing timeout
      if (fadeTimeout.current) {
        clearTimeout(fadeTimeout.current);
      }
      
      // Set new timeout for fade out
      fadeTimeout.current = setTimeout(() => {
        setIsCursorMoving(false);
        setShowTiles(false);
      }, 1500); // Fade out after 1.5 seconds of no movement
    };

    window.addEventListener('mousemove', handleMouseMove);
    
    return () => {
      if (fadeTimeout.current) {
        clearTimeout(fadeTimeout.current);
      }
      if (showTimeout.current) {
        clearTimeout(showTimeout.current);
      }
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

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
    }, 100);

    return () => clearTimeout(timer);
  }, [albumCovers]); 

  return (
    <div className="album-grid-container">
      {/* Dark background overlay */}
      <div className="album-grid-overlay"></div>
      
      {/* Album tiles grid */}
      <div className="album-grid-inner" ref={gridRef}>
        {albumCovers.map((url, index) => {
          const tilePos = tilePositions[index] || { centerX: 0, centerY: 0 };
          
          const distance = Math.sqrt(
            Math.pow(tilePos.centerX - cursorPos.x, 2) + 
            Math.pow(tilePos.centerY - cursorPos.y, 2)
          );
          
          const maxDistance = 400; // Increased highlight radius
          const proximity = Math.min(1, distance / maxDistance);
          
          // Calculate opacity based on distance and cursor movement
          let baseOpacity = 0;
          
          // Only show tiles when cursor is moving and showTiles is true
          if (isCursorMoving && showTiles) {
            baseOpacity = Math.max(0, 1 - proximity);
          }
          
          // Calculate scale and transform
          const scale = 0.8 + (baseOpacity * 0.4); // Scale from 0.8 to 1.2
          const translateY = -(baseOpacity * 20);
          const shadowSize = baseOpacity * 40;
          
          const transform = `scale(${scale}) translateY(${translateY}px)`;
          const boxShadow = `0 10px ${shadowSize}px rgba(78, 161, 255, ${baseOpacity * 0.8})`;
          const zIndex = Math.round(1000 - distance);
          
          return (
            <div
              key={index}
              className="album-tile-wrapper"
              style={{
                transform,
                boxShadow,
                zIndex,
                opacity: baseOpacity > 0.05 ? baseOpacity : 0, // Hide tiles when cursor stops or too far
                transition: 'opacity 0.6s ease-out, transform 0.4s ease-out, box-shadow 0.4s ease-out',
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