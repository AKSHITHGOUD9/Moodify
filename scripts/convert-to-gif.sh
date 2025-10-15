#!/bin/bash

# Convert MP4 videos to GIFs for GitHub README
# Requires ffmpeg to be installed

echo "🎬 Converting MP4 videos to GIFs for GitHub..."

# Create gifs directory
mkdir -p demos/gifs

# Function to convert video to GIF
convert_to_gif() {
    local input="$1"
    local output="$2"
    local duration="$3"
    
    echo "Converting $input to $output..."
    
    # Convert to GIF with optimized settings
    ffmpeg -i "$input" \
        -t "$duration" \
        -vf "fps=10,scale=800:-1:flags=lanczos,palettegen" \
        -y demos/gifs/palette.png
    
    ffmpeg -i "$input" \
        -t "$duration" \
        -i demos/gifs/palette.png \
        -filter_complex "fps=10,scale=800:-1:flags=lanczos[x];[x][1:v]paletteuse" \
        -y "$output"
    
    echo "✅ Created $output"
}

# Convert each video
convert_to_gif "demos/Intro.mp4" "demos/gifs/intro-demo.gif" "30"
convert_to_gif "demos/Charts&Dashboard.mp4" "demos/gifs/dashboard-demo.gif" "45"
convert_to_gif "demos/Creating playlist.mp4" "demos/gifs/playlist-demo.gif" "60"
convert_to_gif "demos/Playlist created in spotify.mp4" "demos/gifs/spotify-demo.gif" "15"

# Clean up palette file
rm -f demos/gifs/palette.png

echo "🎉 All videos converted to GIFs!"
echo "📁 Check the demos/gifs/ folder for the converted files"
echo "📝 Update README.md to use .gif files instead of .mp4"

# Show file sizes
echo ""
echo "📊 File sizes:"
ls -lh demos/gifs/*.gif
