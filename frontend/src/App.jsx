import { useState, useEffect } from "react";
import "./App.css";
import { AuthProvider } from "./contexts/AuthContext";
import LoginPage from "./components/auth/LoginPage";
import Dashboard from "./components/dashboard/Dashboard";
import { useAuth } from "./hooks/useAuth";

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading Moodify...</p>
      </div>
    );
  }

  return (
    <AuthProvider>
      <div className="app">
        {user ? <Dashboard /> : <LoginPage />}
      </div>
    </AuthProvider>
  );
}

export default App;
