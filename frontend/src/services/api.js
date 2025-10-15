const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || "https://moodify-ai-powered.onrender.com";

class ApiService {
  async get(endpoint, params = {}) {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    
    if (params.token) {
      url.searchParams.append("token", params.token);
    }

    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  }

  async post(endpoint, data = {}, params = {}) {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    
    if (params.token) {
      url.searchParams.append("token", params.token);
    }

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }
}

export const apiService = new ApiService();
