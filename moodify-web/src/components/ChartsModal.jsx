import React, { useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale
} from 'chart.js';
import { Line, Bar, Radar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale
);

const ChartsModal = ({ isOpen, onClose, analytics }) => {
  if (!isOpen || !analytics) return null;

  // Theme colors for charts
  const themeColors = {
    primary: '#4FA1FF',
    secondary: '#7B68EE',
    accent: '#00D4AA',
    warning: '#FFB800',
    danger: '#FF4757',
    success: '#2ED573',
    background: 'rgba(255, 255, 255, 0.1)',
    text: '#FFFFFF',
    grid: 'rgba(255, 255, 255, 0.1)'
  };

  // Generate mock daily play counts for the last 30 days
  const generateListeningTrends = () => {
    const days = [];
    const playCounts = [];
    const today = new Date();
    
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      days.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      playCounts.push(Math.floor(Math.random() * 50) + 10); // Mock data
    }

    return {
      labels: days,
      datasets: [{
        label: 'Daily Plays',
        data: playCounts,
        borderColor: themeColors.primary,
        backgroundColor: `${themeColors.primary}20`,
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: themeColors.primary,
        pointBorderColor: themeColors.text,
        pointBorderWidth: 2,
        pointRadius: 4
      }]
    };
  };


  // Artist popularity data
  const generateArtistPopularity = () => {
    const artists = analytics.top_artists?.slice(0, 8) || [];
    return {
      labels: artists.map(artist => artist.name),
      datasets: [{
        label: 'Play Count',
        data: artists.map(() => Math.floor(Math.random() * 100) + 20),
        backgroundColor: themeColors.primary,
        borderColor: themeColors.secondary,
        borderWidth: 1,
        borderRadius: 4,
        borderSkipped: false,
      }]
    };
  };

  // Mood analysis data
  const generateMoodAnalysis = () => {
    const features = ['Energy', 'Valence', 'Danceability', 'Acousticness', 'Instrumentalness', 'Speechiness'];
    const values = [0.8, 0.6, 0.7, 0.3, 0.2, 0.4]; // Mock audio features
    
    return {
      labels: features,
      datasets: [{
        label: 'Audio Features',
        data: values,
        backgroundColor: `${themeColors.accent}40`,
        borderColor: themeColors.accent,
        borderWidth: 2,
        pointBackgroundColor: themeColors.accent,
        pointBorderColor: themeColors.text,
        pointBorderWidth: 2,
        pointRadius: 5
      }]
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: themeColors.text,
          font: {
            size: 12
          }
        }
      },
      title: {
        display: false
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date',
          color: themeColors.text,
          font: {
            size: 13,
            weight: 'bold'
          }
        },
        grid: {
          color: themeColors.grid,
          drawBorder: false
        },
        ticks: {
          color: themeColors.text,
          font: {
            size: 11
          }
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Number of Plays',
          color: themeColors.text,
          font: {
            size: 13,
            weight: 'bold'
          }
        },
        grid: {
          color: themeColors.grid,
          drawBorder: false
        },
        ticks: {
          color: themeColors.text,
          font: {
            size: 11
          }
        }
      }
    }
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: themeColors.text,
          font: {
            size: 12
          }
        }
      },
      title: {
        display: false
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Artists',
          color: themeColors.text,
          font: {
            size: 13,
            weight: 'bold'
          }
        },
        grid: {
          color: themeColors.grid,
          drawBorder: false
        },
        ticks: {
          color: themeColors.text,
          font: {
            size: 11
          }
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Play Count',
          color: themeColors.text,
          font: {
            size: 13,
            weight: 'bold'
          }
        },
        grid: {
          color: themeColors.grid,
          drawBorder: false
        },
        ticks: {
          color: themeColors.text,
          font: {
            size: 11
          }
        }
      }
    }
  };


  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: themeColors.text,
          font: {
            size: 12
          }
        }
      }
    },
    scales: {
      r: {
        grid: {
          color: themeColors.grid
        },
        pointLabels: {
          color: themeColors.text,
          font: {
            size: 11
          }
        },
        ticks: {
          color: themeColors.text,
          font: {
            size: 10
          }
        }
      }
    }
  };

  return (
    <div className="charts-modal-overlay">
      <div className="charts-modal-content">
        <button className="close-charts-btn" onClick={onClose}>✕</button>
        
        <div className="charts-modal-header">
          <h2>Music Analytics Charts</h2>
          <p>Visual insights into your music taste and listening patterns</p>
        </div>

        <div className="charts-grid">
          {/* Listening Trends - Extended */}
          <div className="chart-container extended-chart">
            <h3>📊 Listening Trends</h3>
            <div className="chart-wrapper extended-wrapper">
              <Line data={generateListeningTrends()} options={chartOptions} />
            </div>
          </div>

          {/* Artist Popularity */}
          <div className="chart-container">
            <h3>📈 Artist Popularity</h3>
            <div className="chart-wrapper">
              <Bar data={generateArtistPopularity()} options={barChartOptions} />
            </div>
          </div>

          {/* Mood Analysis */}
          <div className="chart-container">
            <h3>🎭 Mood Analysis</h3>
            <div className="chart-wrapper">
              <Radar data={generateMoodAnalysis()} options={radarOptions} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChartsModal;
