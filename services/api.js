import { channels, content, epgPrograms, epgSlots, rows } from "../data/mockData.js";

const delay = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 80));
export const API_BASE_URL = "http://127.0.0.1:8000";
const viewsToNumber = (value = "0") => Number(String(value).replace("M", "")) || 0;

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function normalizeErrorMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.errors) && payload.errors.length) {
    return payload.errors.map((item) => item.msg || item.message).filter(Boolean).join(" ");
  }
  if (Array.isArray(payload.detail) && payload.detail.length) {
    return payload.detail.map((item) => item.msg || item.message).filter(Boolean).join(" ");
  }
  return fallback;
}

export async function apiRequest(path, { method = "GET", body, token, headers = {} } = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers
      },
      body: body ? JSON.stringify(body) : undefined
    });
  } catch {
    throw new ApiError("Backend is unreachable.", 0);
  }

  const raw = await response.text();
  const payload = raw ? JSON.parse(raw) : null;

  if (!response.ok) {
    throw new ApiError(
      normalizeErrorMessage(payload, "Request failed."),
      response.status,
      payload
    );
  }

  return payload;
}

export const api = {
  getFeatured() {
    return delay([...content].sort((a, b) => viewsToNumber(b.monthlyViews) - viewsToNumber(a.monthlyViews))[0]);
  },
  getRows() {
    const mapped = Object.fromEntries(
      Object.entries(rows).map(([title, ids]) => [title, ids.map((id) => content.find((item) => item.id === id))])
    );
    return delay(mapped);
  },
  getContentById(id) {
    return delay(content.find((item) => item.id === id));
  },
  getContentByCategory(category) {
    return delay(category === "All" ? content : content.filter((item) => item.category === category));
  },
  searchSemantic(query) {
    const lowered = query.toLowerCase();
    const results = content
      .filter((item) => `${item.title} ${item.category} ${item.description}`.toLowerCase().includes("ai") || lowered.includes(item.category.toLowerCase()) || item.relevance > 84)
      .sort((a, b) => b.relevance - a.relevance);
    return delay(results);
  },
  getLiveTv() {
    return delay({ channels, epgSlots, epgPrograms });
  }
};
