const AUTH_KEY = "synapse.auth.user";

const demoUser = {
  id: "u-demo",
  username: "Rümeysa Aksoy",
  email: "rumeysa@university.edu",
  avatar: "RA",
  interests: ["Artificial Intelligence", "Live Sports", "Documentaries", "Science"],
  preferredCategories: ["Technology", "Science", "Sports", "Movies"]
};

export function getCurrentUser() {
  const stored = localStorage.getItem(AUTH_KEY);
  return stored ? JSON.parse(stored) : null;
}

export function login(email, password) {
  const user = { ...demoUser, email: email || demoUser.email };
  localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  return Promise.resolve({ user, token: "mock-jwt-token-for-fastapi-later" });
}

export function register(payload) {
  const initials = payload.username
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const user = { ...demoUser, ...payload, avatar: initials || "ST" };
  localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  return Promise.resolve({ user, token: "mock-jwt-token-for-fastapi-later" });
}

export function logout() {
  localStorage.removeItem(AUTH_KEY);
}
