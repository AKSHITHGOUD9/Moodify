/**
 * Main Entry Point for Moodify Application
 * 
 * This file initializes the React application and renders the main App component.
 * Uses React 18's createRoot API for optimal performance and StrictMode for
 * development-time checks and warnings.
 * 
 * Features:
 * - React 18 concurrent rendering
 * - StrictMode for development safety
 * - Global CSS imports
 * - Clean, minimal setup
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Initialize React application with performance optimizations
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
