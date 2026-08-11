import { ApiError, apiRequest } from "./api.js";

const MOCK_USER_KEY = "synapse.mock.user";
const MOCK_TOKEN = "mock-jwt-token-for-frontend-demo";

function makeMockProfile(payload = {}) {
  const username = payload.username || payload.email?.split("@")[0] || "vynex-user";
  const displayName = payload.display_name || payload.displayName || username;

  return {
    id: 1,
    username,
    email: payload.email || "demo@vynex.local",
    role: "user",
    created_at: new Date().toISOString(),
    profile: {
      display_name: displayName,
      avatar_url: payload.avatar_url || null,
      interests: payload.interests || ["Artificial Intelligence", "Sports", "Science"],
      preferred_categories: payload.preferred_categories || payload.preferredCategories || ["Technology", "Documentaries"]
    }
  };
}

function shouldUseMockFallback(error) {
  return error instanceof ApiError && (error.status === 0 || error.status === 404);
}

function mockAuthResponse(payload = {}) {
  const user = makeMockProfile(payload);
  localStorage.setItem(MOCK_USER_KEY, JSON.stringify(user));
  return {
    access_token: MOCK_TOKEN,
    token_type: "bearer",
    user
  };
}

async function withMockFallback(request, fallback) {
  try {
    return await request();
  } catch (error) {
    if (shouldUseMockFallback(error)) return fallback();
    throw error;
  }
}

export const authService = {
  register(payload) {
    return withMockFallback(
      () => apiRequest("/api/auth/register", {
        method: "POST",
        body: payload
      }),
      () => mockAuthResponse(payload)
    );
  },
  login(payload) {
    return withMockFallback(
      () => apiRequest("/api/auth/login", {
        method: "POST",
        body: payload
      }),
      () => mockAuthResponse(payload)
    );
  },
  getCurrentUser(token) {
    if (token === MOCK_TOKEN) {
      return Promise.resolve(JSON.parse(localStorage.getItem(MOCK_USER_KEY)) || makeMockProfile());
    }

    return withMockFallback(
      () => apiRequest("/api/auth/me", {
        token
      }),
      () => JSON.parse(localStorage.getItem(MOCK_USER_KEY)) || makeMockProfile()
    );
  },
  updateProfile(token, payload) {
    return withMockFallback(
      () => apiRequest("/api/users/me/profile", {
        method: "PATCH",
        token,
        body: payload
      }),
      () => {
        const user = JSON.parse(localStorage.getItem(MOCK_USER_KEY)) || makeMockProfile();
        const updated = {
          ...user,
          profile: {
            ...user.profile,
            ...payload
          }
        };
        localStorage.setItem(MOCK_USER_KEY, JSON.stringify(updated));
        return updated;
      }
    );
  }
};
