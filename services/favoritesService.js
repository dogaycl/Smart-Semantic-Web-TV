import { isAuthenticated } from "../contexts/authContext.js";
import { ApiError, api } from "./api.js?v=21";

const KEY = "synapse.my-list";

let favoritesCache = [];
let favoritesLoaded = false;
let favoritesPromise = null;
let authListenerBound = false;

function emitFavoritesChanged() {
  document.dispatchEvent(new CustomEvent("favorites:changed"));
}

function loadCachedFavorites() {
  const stored = localStorage.getItem(KEY);
  if (!stored) return [];
  try {
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed.map((item) => String(item)) : [];
  } catch {
    return [];
  }
}

function persistFavorites() {
  localStorage.setItem(KEY, JSON.stringify(favoritesCache));
}

function setFavorites(nextFavorites, { notify = true } = {}) {
  favoritesCache = [...new Set((nextFavorites || []).map((item) => String(item)).filter(Boolean))];
  favoritesLoaded = true;
  persistFavorites();
  if (notify) emitFavoritesChanged();
  return favoritesCache;
}

function clearFavorites({ notify = true } = {}) {
  favoritesCache = [];
  favoritesLoaded = false;
  favoritesPromise = null;
  localStorage.removeItem(KEY);
  if (notify) emitFavoritesChanged();
}

function bindAuthListener() {
  if (authListenerBound) return;
  authListenerBound = true;

  document.addEventListener("auth:changed", () => {
    if (!isAuthenticated()) {
      clearFavorites({ notify: false });
      return;
    }
    favoritesCache = loadCachedFavorites();
    favoritesLoaded = false;
    void ensureFavoritesLoaded({ force: true }).catch(() => {});
  });
}

bindAuthListener();
favoritesCache = loadCachedFavorites();

export function getFavorites() {
  return favoritesCache;
}

export async function ensureFavoritesLoaded({ force = false } = {}) {
  bindAuthListener();

  if (!isAuthenticated()) {
    clearFavorites({ notify: false });
    return favoritesCache;
  }

  if (favoritesLoaded && !force) {
    return favoritesCache;
  }

  if (favoritesPromise && !force) {
    return favoritesPromise;
  }

  favoritesPromise = api.getMyFavorites()
    .then((favorites) => setFavorites(favorites))
    .catch((error) => {
      if (error instanceof ApiError && error.status === 401) {
        clearFavorites({ notify: false });
        return favoritesCache;
      }
      throw error;
    })
    .finally(() => {
      favoritesPromise = null;
    });

  return favoritesPromise;
}

export function isFavorite(id) {
  return getFavorites().includes(String(id));
}

export async function toggleFavorite(id) {
  const favoriteId = String(id);
  if (!isAuthenticated()) {
    throw new ApiError("You are not authenticated.", 401);
  }

  const favorites = await ensureFavoritesLoaded();
  if (favorites.includes(favoriteId)) {
    await api.removeMyFavorite(favoriteId);
    return setFavorites(favorites.filter((item) => item !== favoriteId));
  }

  await api.addMyFavorite(favoriteId);
  return setFavorites([...favorites, favoriteId]);
}
