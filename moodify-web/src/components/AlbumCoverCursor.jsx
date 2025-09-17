import { useEffect, useState, useRef } from 'react';

const API = import.meta.env.VITE_BACKEND_URL;

const AlbumCoverCursor = () => {
  const [albumCovers, setAlbumCovers] = useState([]);
  const [availableUrls, setAvailableUrls] = useState([]);
  const lastMousePosition = useRef({ x: 0, y: 0 });

  // Fetch album cover URLs from the new backend endpoint
  useEffect(() => {
    const fetchCovers = async () => {
      try {
        const res = await fetch(`${API}/api/album-covers`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to fetch album covers");
        const data = await res.json();
        setAvailableUrls(data.urls);
      } catch (e) {
        console.error(e);
      }
    };
    fetchCovers();
  }, []);

  // Handle mouse movement and image creation
  useEffect(() => {
    const handleMouseMove = (e) => {
      // Check if we have URLs and enough distance has been moved
      const distance = Math.sqrt(
        (e.clientX - lastMousePosition.current.x) ** 2 +
        (e.clientY - lastMousePosition.current.y) ** 2
      );
      if (distance < 50 || availableUrls.length === 0) { // Throttle image creation
        return;
      }
      lastMousePosition.current = { x: e.clientX, y: e.clientY };

      const newCover = {
        id: Date.now(),
        url: availableUrls[Math.floor(Math.random() * availableUrls.length)],
        x: e.clientX + (Math.random() * 40 - 20), // Add a small random offset
        y: e.clientY + (Math.random() * 40 - 20),
        opacity: 1,
      };

      // Add the new cover and start the fade-out process
      setAlbumCovers((prevCovers) => {
        const updatedCovers = [...prevCovers, newCover];
        // Clean up old covers to prevent memory leaks
        return updatedCovers.slice(-20); // Keep max 20 images on screen
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [availableUrls]);
  
  // Use a different useEffect to manage the fade-out logic separately
  useEffect(() => {
    const fadeOutTimer = setInterval(() => {
      setAlbumCovers((prevCovers) =>
        prevCovers.map((cover) => ({
          ...cover,
          opacity: cover.opacity - 0.05, // Decrease opacity over time
        })).filter(cover => cover.opacity > 0)
      );
    }, 100);
    
    return () => clearInterval(fadeOutTimer);
  }, []);


  return (
    <div className="album-cover-cursor-container">
      {albumCovers.map((cover) => (
        <img
          key={cover.id}
          src={cover.url}
          alt="Album Cover"
          className="cursor-album-cover"
          style={{
            left: cover.x,
            top: cover.y,
            opacity: cover.opacity,
            transform: `scale(${cover.opacity + 0.5})`, // Scale down as it fades
            transition: 'opacity 0.2s, transform 0.2s',
          }}
        />
      ))}
    </div>
  );
};

export default AlbumCoverCursor;