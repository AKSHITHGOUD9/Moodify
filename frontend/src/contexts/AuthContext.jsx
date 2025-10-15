import { createContext, useContext, useState, useEffect } from "react";
import { authService } from "../services/auth";

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("spotifyToken");
    if (token) {
      loadUser(token);
    } else {
      setLoading(false);
    }
  }, []);

  const loadUser = async (token) => {
    try {
      setLoading(true);
      const userData = await authService.getCurrentUser(token);
      setUser(userData);
    } catch (err) {
      console.error("Failed to load user:", err);
      localStorage.removeItem("spotifyToken");
      setError("Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const login = async () => {
    try {
      const { auth_url } = await authService.getAuthUrl();
      window.location.href = auth_url;
    } catch (err) {
      setError("Failed to initiate login");
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      setUser(null);
      localStorage.removeItem("spotifyToken");
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    loadUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
