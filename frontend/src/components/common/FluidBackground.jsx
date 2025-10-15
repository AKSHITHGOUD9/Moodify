import { useState, useEffect } from "react";

export default function FluidBackground() {
  const [albumCovers, setAlbumCovers] = useState([]);

  useEffect(() => {
    // Default album covers for fluid animation
    const defaultCovers = [
      "https://i.scdn.co/image/ab67616d0000b273c8a11e48c91a982d086afc69", // Spotify default
      "https://i.scdn.co/image/ab67616d0000b273b0d4b4c4b4c4b4c4b4c4b4c4", // Another default
      "https://i.scdn.co/image/ab67616d0000b273d0e5e5e5e5e5e5e5e5e5e5e5", // Another default
      "https://i.scdn.co/image/ab67616d0000b273e0f6f6f6f6f6f6f6f6f6f6f6", // Another default
      "https://i.scdn.co/image/ab67616d0000b273f0g7g7g7g7g7g7g7g7g7g7g7"  // Another default
    ];

    // Try to fetch real album covers from backend
    const fetchAlbumCovers = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_BACKEND_URL || "https://moodify-ai-powered.onrender.com"}/api/album-covers`);
        if (response.ok) {
          const covers = await response.json();
          if (covers && covers.length > 0) {
            setAlbumCovers(covers.slice(0, 10)); // Use first 10 covers
            return;
          }
        }
      } catch (error) {
        console.log("Using default album covers for fluid background");
      }
      
      // Fallback to default covers
      setAlbumCovers(defaultCovers);
    };

    fetchAlbumCovers();
  }, []);

  return (
    <div className="fluid-background">
      {albumCovers.map((cover, index) => (
        <img
          key={index}
          src={cover}
          alt="Album cover"
          className="fluid-cover"
          style={{
            width: `${Math.random() * 100 + 50}px`,
            height: `${Math.random() * 100 + 50}px`,
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 20}s`,
            animationDuration: `${20 + Math.random() * 15}s`
          }}
        />
      ))}
    </div>
  );
}
