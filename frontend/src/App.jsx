import "./App.css";
import { AuthProvider } from "./contexts/AuthContext";
import LoginPage from "./components/auth/LoginPage";
import Dashboard from "./components/dashboard/Dashboard";
import { useAuth } from "./hooks/useAuth";

function AppContent() {
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
    <div className="app">
      {user ? <Dashboard /> : <LoginPage />}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
