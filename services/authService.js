import { apiRequest } from "./api.js";

export const authService = {
  register(payload) {
    return apiRequest("/api/auth/register", {
      method: "POST",
      body: payload
    });
  },
  login(payload) {
    return apiRequest("/api/auth/login", {
      method: "POST",
      body: payload
    });
  },
  getCurrentUser(token) {
    return apiRequest("/api/auth/me", {
      token
    });
  },
  updateProfile(token, payload) {
    return apiRequest("/api/users/me/profile", {
      method: "PATCH",
      token,
      body: payload
    });
  }
};
