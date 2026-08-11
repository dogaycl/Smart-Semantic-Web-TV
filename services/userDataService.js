const RATINGS_KEY = "vynex.ratings";
const HISTORY_KEY = "vynex.watch-history";
const COMMENTS_KEY = "vynex.comments";
const PROFILE_KEY = "vynex.active-profile";
const AI_PREFS_KEY = "vynex.ai-preferences";

const defaultHistory = [
  { contentId: "dune-part-two", progress: 68, watchedAt: "Today", device: "Web TV" },
  { contentId: "stranger-things", progress: 42, watchedAt: "Yesterday", device: "Tablet" },
  { contentId: "interstellar", progress: 100, watchedAt: "This week", device: "Living Room" }
];

const defaultComments = {
  "dune-part-two": [
    { author: "Ece", text: "The visual world is incredible, and the second half is very strong.", spoiler: false, likes: 12 },
    { author: "Mert", text: "The final scene connects beautifully with the book.", spoiler: true, likes: 5 }
  ]
};

function read(key, fallback) {
  const value = localStorage.getItem(key);
  return value ? JSON.parse(value) : fallback;
}

function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
  return value;
}

export function getRatings() {
  return read(RATINGS_KEY, { "dune-part-two": 5, interstellar: 5, "black-mirror": 4 });
}

export function rateContent(contentId, rating) {
  return write(RATINGS_KEY, { ...getRatings(), [contentId]: Number(rating) });
}

export function getWatchHistory() {
  return read(HISTORY_KEY, defaultHistory);
}

export function addHistory(contentId, progress = 12) {
  const next = [{ contentId, progress, watchedAt: "Just now", device: "Browser" }, ...getWatchHistory().filter((item) => item.contentId !== contentId)];
  return write(HISTORY_KEY, next.slice(0, 12));
}

export function getComments(contentId) {
  return read(COMMENTS_KEY, defaultComments)[contentId] || [];
}

export function addComment(contentId, comment) {
  const comments = read(COMMENTS_KEY, defaultComments);
  const next = {
    ...comments,
    [contentId]: [{ ...comment, likes: 0 }, ...(comments[contentId] || [])]
  };
  write(COMMENTS_KEY, next);
  return next[contentId];
}

export function likeComment(contentId, index) {
  const comments = read(COMMENTS_KEY, defaultComments);
  const list = [...(comments[contentId] || [])];
  list[index] = { ...list[index], likes: list[index].likes + 1 };
  write(COMMENTS_KEY, { ...comments, [contentId]: list });
  return list;
}

export function getActiveProfile() {
  return localStorage.getItem(PROFILE_KEY) || "Main";
}

export function setActiveProfile(name) {
  localStorage.setItem(PROFILE_KEY, name);
  document.dispatchEvent(new CustomEvent("profile:selected"));
}

export function getAiPreferences() {
  return read(AI_PREFS_KEY, {
    useMinImdb: true,
    minImdb: 7.5,
    usePopularity: true,
    popularity: 70,
    useMaxDuration: true,
    maxDurationMinutes: 180,
    useReleaseAfter: true,
    releaseAfter: 2010,
    useDiscoveryLevel: true,
    discoveryLevel: 45,
    useMood: false,
    preferredMood: "Mind-bending",
    contentTypes: ["Movies", "Series", "Documentaries", "Science", "Technology"],
    avoidSpoilers: true,
    familySafe: false
  });
}

export function saveAiPreferences(preferences) {
  write(AI_PREFS_KEY, preferences);
  document.dispatchEvent(new CustomEvent("ai-preferences:changed"));
  return preferences;
}
