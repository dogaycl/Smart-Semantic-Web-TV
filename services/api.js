import {
  buildCatalogRows,
  filterCatalogForAi,
  normalizeCatalogDetail,
  normalizeCatalogSummary,
  pickFeaturedCatalogItem
} from "./catalogMapper.js";

export const API_BASE_URL = "http://127.0.0.1:8000";
const AUTH_TOKEN_KEY = "synapse.auth.token";

let catalogCache = null;
let catalogCachePromise = null;

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
  let payload = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = { detail: raw };
    }
  }

  if (!response.ok) {
    throw new ApiError(
      normalizeErrorMessage(payload, "Request failed."),
      response.status,
      payload
    );
  }

  return payload;
}

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value == null || value === "") return;
    if (Array.isArray(value)) {
      if (value.length) query.set(key, value.join(","));
      return;
    }
    query.set(key, String(value));
  });
  return query.toString();
}

async function fetchCatalogList(path, params = {}) {
  const query = buildQuery(params);
  const payload = await apiRequest(query ? `${path}?${query}` : path);
  return {
    ...payload,
    items: (payload.items || []).map(normalizeCatalogSummary)
  };
}

async function getCatalogCache({ force = false } = {}) {
  if (catalogCache && !force) return catalogCache;
  if (catalogCachePromise && !force) return catalogCachePromise;

  catalogCachePromise = fetchCatalogList("/api/catalog", {
    sort: "popularity_desc",
    limit: 200
  })
    .then((payload) => {
      catalogCache = payload.items;
      return catalogCache;
    })
    .finally(() => {
      catalogCachePromise = null;
    });

  return catalogCachePromise;
}

function getStoredToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function normalizeDiscoveryResult(item) {
  const isLive = item.result_type === "live_program";
  return {
    id: item.content_slug || item.id,
    slug: item.content_slug || null,
    contentType: item.result_type === "movie" ? "movie" : item.result_type === "series" ? "tv" : "live",
    title: item.title,
    category: item.category_label,
    primaryGenre: item.genres?.[0] || item.category_label,
    genres: item.genres || [],
    year: item.year,
    releaseDate: item.release_date,
    duration: item.runtime_display || item.availability?.label || "On demand",
    runtimeMinutes: item.runtime_minutes,
    imdb: item.rating != null ? item.rating.toFixed(1) : null,
    ratingValue: item.rating,
    popularityValue: item.popularity,
    description: item.description || item.explanation || (isLive ? "Live recommendation." : "No description is available yet."),
    poster: item.poster_url || item.channel?.logo_url || null,
    backdrop: item.backdrop_url || item.poster_url || item.channel?.logo_url || null,
    status: isLive ? item.availability?.label : "On demand",
    language: item.language ? String(item.language).toUpperCase() : null,
    routePath: isLive ? "#/live-tv" : `#/content/${item.content_slug}`,
    liveChannelId: isLive ? item.channel?.id : null,
    disableFavorite: isLive,
    recommendationReason: item.explanation,
    searchScore: item.score,
    availability: item.availability || null,
    channel: item.channel || null
  };
}

function normalizeViewingPlanItem(item) {
  const isLive = item.result_type === "live_program";
  return {
    id: item.content_slug || item.candidate_id,
    candidateId: item.candidate_id,
    resultType: item.result_type,
    title: item.title,
    description: item.description || "",
    category: item.category_label,
    primaryGenre: item.genres?.[0] || item.category_label,
    genres: item.genres || [],
    runtimeMinutes: item.runtime_minutes,
    runtimeDisplay: item.runtime_display || "Scheduled",
    plannedStart: item.planned_start,
    plannedEnd: item.planned_end,
    availabilityStart: item.availability_start,
    availabilityEnd: item.availability_end,
    recommendationReason: item.reason,
    recommendationScore: item.recommendation_score,
    poster: item.poster_url || item.channel?.logo_url || null,
    backdrop: item.backdrop_url || item.poster_url || item.channel?.logo_url || null,
    contentSlug: item.content_slug || null,
    routePath: isLive ? "#/live-tv" : (item.content_slug ? `#/content/${item.content_slug}` : "#/on-demand"),
    liveChannelId: isLive ? item.channel?.id : null,
    channel: item.channel || null
  };
}

function normalizeViewingPlan(plan) {
  return {
    id: plan.id,
    planDate: plan.plan_date,
    timezone: plan.timezone,
    availableStart: plan.available_start,
    availableEnd: plan.available_end,
    maxDurationMinutes: plan.max_duration_minutes,
    includeLive: plan.include_live,
    includeVod: plan.include_vod,
    preferredCategories: plan.preferred_categories || [],
    preferenceText: plan.preference_text || "",
    profileSummary: plan.profile_summary || [],
    summary: plan.summary,
    generationSource: plan.generation_source,
    llmModel: plan.llm_model || null,
    llmRepairApplied: Boolean(plan.llm_repair_applied),
    createdAt: plan.created_at,
    updatedAt: plan.updated_at,
    items: (plan.items || []).map(normalizeViewingPlanItem)
  };
}

export const api = {
  async getCatalog({ contentType = null, category = null, genre = null, search = null, sort = "popularity_desc", limit = 48, offset = 0, slugs = null } = {}) {
    const endpoint = contentType === "movie" ? "/api/catalog/movies" : contentType === "tv" ? "/api/catalog/series" : "/api/catalog";
    return fetchCatalogList(endpoint, {
      category,
      genre,
      search,
      sort,
      limit,
      offset,
      slugs
    });
  },
  async getAllCatalog(options = {}) {
    return getCatalogCache(options);
  },
  async getFeatured() {
    const items = await getCatalogCache();
    return pickFeaturedCatalogItem(items);
  },
  async getRows() {
    const items = await getCatalogCache();
    return buildCatalogRows(items);
  },
  async getContentById(id) {
    const payload = await apiRequest(`/api/catalog/${id}`);
    return normalizeCatalogDetail(payload);
  },
  async getContentByCategory(category, { contentType = null, search = null, sort = "popularity_desc", limit = 96 } = {}) {
    const response = await this.getCatalog({
      contentType,
      category: category === "All" ? null : category,
      search,
      sort,
      limit
    });
    return response.items;
  },
  async getCatalogBySlugs(slugs = []) {
    if (!slugs.length) return [];
    const response = await this.getCatalog({
      slugs,
      limit: Math.max(slugs.length, 1)
    });
    const bySlug = new Map(response.items.map((item) => [item.slug, item]));
    return slugs.map((slug) => bySlug.get(slug)).filter(Boolean);
  },
  async getAiTunedCatalog(preferences) {
    try {
      const recommendations = await this.getRecommendations({ limit: 8, windowHours: 12 });
      if (recommendations.length) return recommendations;
    } catch {}
    const items = await getCatalogCache();
    return filterCatalogForAi(items, preferences);
  },
  async searchSemantic(query, { limit = 12, windowHours = 24 } = {}) {
    const token = getStoredToken();
    const payload = await apiRequest("/api/search/semantic", {
      method: "POST",
      token,
      body: {
        query,
        limit,
        window_hours: windowHours
      }
    });
    return (payload.results || []).map(normalizeDiscoveryResult);
  },
  async getRecommendations({ limit = 8, windowHours = 12 } = {}) {
    const token = getStoredToken();
    if (!token) return [];
    const query = buildQuery({
      limit,
      window_hours: windowHours
    });
    const payload = await apiRequest(`/api/recommendations?${query}`, {
      token
    });
    return (payload.results || []).map(normalizeDiscoveryResult);
  },
  async getLiveTv({ windowHours = 4, slotMinutes = 60 } = {}) {
    const start = new Date();
    start.setMinutes(0, 0, 0);
    const end = new Date(start.getTime() + (windowHours * 60 * 60 * 1000));
    const query = new URLSearchParams({
      start: start.toISOString(),
      end: end.toISOString(),
      slot_minutes: String(slotMinutes)
    });

    const [channels, epg] = await Promise.all([
      apiRequest(`/api/channels?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`),
      apiRequest(`/api/epg?${query.toString()}`)
    ]);

    return { channels, epg };
  },
  getChannelLive(channelId) {
    return apiRequest(`/api/channels/${channelId}/live`);
  },
  async generateViewingPlan(payload) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const plan = await apiRequest("/api/viewing-plans/generate", {
      method: "POST",
      token,
      body: payload
    });
    return normalizeViewingPlan(plan);
  },
  async getViewingPlans() {
    const token = getStoredToken();
    if (!token) return [];
    const payload = await apiRequest("/api/viewing-plans", {
      token
    });
    return (payload.items || []).map(normalizeViewingPlan);
  },
  async getViewingPlan(planId) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const payload = await apiRequest(`/api/viewing-plans/${planId}`, {
      token
    });
    return normalizeViewingPlan(payload);
  }
};
