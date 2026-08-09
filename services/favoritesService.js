const KEY = "synapse.my-list";
const defaults = ["ai-odyssey", "robotics-frontier", "istanbul-derby-live"];

export function getFavorites() {
  const stored = localStorage.getItem(KEY);
  return stored ? JSON.parse(stored) : defaults;
}

export function isFavorite(id) {
  return getFavorites().includes(id);
}

export function toggleFavorite(id) {
  const favorites = getFavorites();
  const next = favorites.includes(id) ? favorites.filter((item) => item !== id) : [...favorites, id];
  localStorage.setItem(KEY, JSON.stringify(next));
  document.dispatchEvent(new CustomEvent("favorites:changed"));
  return next;
}
