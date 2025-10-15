import { apiService } from "./api";

export const authService = {
  async getAuthUrl() {
    return await apiService.get("/login");
  },

  async getCurrentUser(token) {
    return await apiService.get("/me", { token });
  },

  async logout() {
    return await apiService.post("/logout");
  }
};
