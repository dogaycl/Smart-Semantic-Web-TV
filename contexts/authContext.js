import { authService } from "../services/authService.js";
import { ApiError } from "../services/api.js?v=31";

const AUTH_TOKEN_KEY = "synapse.auth.token";

let currentUser = null;
let authReady = false;
let initializationPromise = null;
let accessToken = localStorage.getItem(AUTH_TOKEN_KEY);

function makeAvatarLabel(value) {
  return (value || "")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "ST";
}

function normalizeUser(user) {
  const displayName = user.profile?.display_name || user.username;
  return {
    id: user.id,
    username: user.username,
    displayName,
    email: user.email,
    role: user.role,
    createdAt: user.created_at,
    avatar: makeAvatarLabel(displayName),
    avatarUrl: user.profile?.avatar_url || null,
    interests: user.profile?.interests || [],
    preferredCategories: user.profile?.preferred_categories || []
  };
}

function emitAuthChanged() {
  document.dispatchEvent(new CustomEvent("auth:changed"));
}

export function getAccessToken() {
  return accessToken || localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getCurrentUser() {
  return currentUser;
}

export function isAuthReady() {
  return authReady;
}

export function isAuthenticated() {
  return Boolean(currentUser && getAccessToken());
}

function setSession({ token, user, notify = true }) {
  if (token) {
    accessToken = token;
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  }
  currentUser = normalizeUser(user);
  authReady = true;
  if (notify) emitAuthChanged();
  return currentUser;
}

function clearSession({ notify = true } = {}) {
  accessToken = null;
  localStorage.removeItem(AUTH_TOKEN_KEY);
  currentUser = null;
  authReady = true;
  if (notify) emitAuthChanged();
}

export async function initializeAuth() {
  if (authReady) return currentUser;
  if (initializationPromise) return initializationPromise;

  initializationPromise = (async () => {
    const token = getAccessToken();
    if (!token) {
      clearSession({ notify: false });
      initializationPromise = null;
      return null;
    }

    try {
      const user = await authService.getCurrentUser(token);
      setSession({ token, user, notify: false });
    } catch (error) {
      clearSession({ notify: false });
      if (!(error instanceof ApiError)) {
        throw error;
      }
    } finally {
      authReady = true;
      initializationPromise = null;
    }

    return currentUser;
  })();

  return initializationPromise;
}

export async function login(email, password) {
  const response = await authService.login({ email, password });
  setSession({ token: response.access_token, user: response.user });
  return currentUser;
}

export async function register(payload) {
  const response = await authService.register(payload);
  setSession({ token: response.access_token, user: response.user });
  return currentUser;
}

export async function updateProfile(payload) {
  const token = getAccessToken();
  if (!token) {
    clearSession();
    throw new ApiError("You are not authenticated.", 401);
  }

  try {
    const user = await authService.updateProfile(token, payload);
    setSession({ token, user, notify: false });
    return currentUser;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearSession();
    }
    throw error;
  }
}

export function logout() {
  clearSession();
}
