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

export async function apiRequest(path, { method = "GET", body, token, headers = {}, timeoutMs = 20000 } = {}) {
  let response;
  const controller = typeof AbortController === "function" ? new AbortController() : null;
  const timeout = controller
    ? window.setTimeout(() => {
      controller.abort();
    }, timeoutMs)
    : null;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      cache: "no-store",
      signal: controller?.signal,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers
      },
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (error) {
    if (timeout) window.clearTimeout(timeout);
    if (error?.name === "AbortError") {
      throw new ApiError("The server took too long to respond.", 0);
    }
    throw new ApiError("Unable to connect to server.", 0);
  }
  if (timeout) window.clearTimeout(timeout);

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
    limit: 300
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

function normalizePlaybackSource(source) {
  if (!source) return null;
  return {
    id: source.id,
    name: source.name,
    type: source.type,
    playbackUrl: source.playback_url,
    embedUrl: source.embed_url,
    externalVideoId: source.external_video_id,
    quality: source.quality,
    language: source.language ? String(source.language).toUpperCase() : null,
    isPrimary: Boolean(source.is_primary),
    providerName: source.provider_name || null,
    providerUrl: source.provider_url || null,
    licenseNote: source.license_note || null,
    sourceNote: source.source_note || null,
    lastCheckedAt: source.last_checked_at || null,
    error: source.error || null,
    capabilities: source.capabilities || {
      can_play: false,
      can_pause: false,
      can_seek: false,
      can_report_progress: false,
      can_fullscreen: true,
      supports_seek: false,
      supports_state_tracking: false
    }
  };
}

function normalizePlayback(payload) {
  if (!payload) return null;
  return {
    contentId: payload.content_id,
    slug: payload.slug,
    title: payload.title,
    playbackAvailable: Boolean(payload.playback_available),
    watchAction: payload.watch_action,
    message: payload.message,
    primarySource: normalizePlaybackSource(payload.primary_source),
    sources: (payload.sources || []).map(normalizePlaybackSource),
    trailer: payload.trailer || null,
    fallback: payload.fallback
      ? {
          type: payload.fallback.type,
          label: payload.fallback.label,
          message: payload.fallback.message || "",
          embedUrl: payload.fallback.embed_url || null
        }
      : null,
    watchProgress: payload.watch_progress
      ? {
          watchPositionSeconds: payload.watch_progress.watch_position_seconds,
          totalWatchedDurationSeconds: payload.watch_progress.total_watched_duration_seconds,
          isCompleted: Boolean(payload.watch_progress.is_completed),
          lastWatchedAt: payload.watch_progress.last_watched_at
        }
      : null
  };
}

function normalizeWatchHistoryEntry(entry) {
  return {
    contentId: entry.content_id,
    contentType: entry.content_type,
    watchPositionSeconds: entry.watch_position_seconds,
    totalWatchedDurationSeconds: entry.total_watched_duration_seconds,
    isCompleted: Boolean(entry.is_completed),
    lastWatchedAt: entry.last_watched_at,
    createdAt: entry.created_at,
    updatedAt: entry.updated_at
  };
}

function normalizeWatchPartyParticipant(entry) {
  return {
    userId: entry.user_id,
    username: entry.username,
    displayName: entry.display_name,
    avatarUrl: entry.avatar_url || null,
    isHost: Boolean(entry.is_host),
    joinedAt: entry.joined_at,
    lastSeenAt: entry.last_seen_at || null,
    isConnected: Boolean(entry.is_connected)
  };
}

function normalizeWatchPartyMessage(entry) {
  return {
    id: entry.id,
    userId: entry.user_id,
    username: entry.username,
    displayName: entry.display_name,
    avatarUrl: entry.avatar_url || null,
    messageText: entry.message_text,
    createdAt: entry.created_at
  };
}

function normalizeWatchPartyTarget(entry) {
  return {
    targetType: entry.target_type,
    contentSlug: entry.content_slug || null,
    channelId: entry.channel_id || null,
    title: entry.title,
    subtitle: entry.subtitle || null,
    posterUrl: entry.poster_url || null,
    backdropUrl: entry.backdrop_url || null,
    liveStatus: entry.live_status || null,
    playbackSupported: Boolean(entry.playback_supported)
  };
}

function normalizeWatchPartyRoom(entry) {
  return {
    id: entry.id,
    roomCode: entry.room_code,
    hostUserId: entry.host_user_id,
    status: entry.status,
    privacy: entry.privacy,
    playbackState: entry.playback_state,
    currentPosition: entry.current_position,
    authoritativePosition: entry.authoritative_position,
    createdAt: entry.created_at,
    updatedAt: entry.updated_at
  };
}

function normalizeWatchPartyDetail(payload) {
  if (!payload) return null;
  return {
    room: normalizeWatchPartyRoom(payload.room),
    target: normalizeWatchPartyTarget(payload.target),
    role: payload.role || null,
    joined: Boolean(payload.joined),
    invitePath: payload.invite_path,
    websocketUrl: payload.websocket_url,
    participants: (payload.participants || []).map(normalizeWatchPartyParticipant),
    recentMessages: (payload.recent_messages || []).map(normalizeWatchPartyMessage),
    hostReconnectGraceSeconds: payload.host_reconnect_grace_seconds
  };
}

function normalizeWatchPartyEvent(payload) {
  if (!payload?.type) return payload;

  if (payload.type === "ROOM_STATE") {
    return {
      type: payload.type,
      room: normalizeWatchPartyRoom(payload.room),
      target: normalizeWatchPartyTarget(payload.target),
      participants: (payload.participants || []).map(normalizeWatchPartyParticipant),
      recentMessages: (payload.recent_messages || []).map(normalizeWatchPartyMessage),
      serverTimestamp: payload.server_timestamp,
      driftThresholdSeconds: payload.drift_threshold_seconds
    };
  }

  if (payload.type === "USER_JOINED" || payload.type === "USER_LEFT") {
    return {
      type: payload.type,
      participant: normalizeWatchPartyParticipant(payload.participant),
      serverTimestamp: payload.server_timestamp
    };
  }

  if (payload.type === "SYNC_STATE") {
    return {
      type: payload.type,
      roomCode: payload.room_code,
      playbackState: payload.playback_state,
      authoritativePosition: payload.authoritative_position,
      serverTimestamp: payload.server_timestamp,
      driftThresholdSeconds: payload.drift_threshold_seconds
    };
  }

  if (payload.type === "PLAY" || payload.type === "PAUSE" || payload.type === "SEEK" || payload.type === "CONTENT_CHANGE") {
    return {
      type: payload.type,
      roomCode: payload.room_code,
      playbackState: payload.playback_state,
      authoritativePosition: payload.authoritative_position,
      serverTimestamp: payload.server_timestamp,
      participant: payload.participant ? normalizeWatchPartyParticipant(payload.participant) : null,
      target: payload.target ? normalizeWatchPartyTarget(payload.target) : null
    };
  }

  if (payload.type === "CHAT_MESSAGE") {
    return {
      type: payload.type,
      message: normalizeWatchPartyMessage(payload.message),
      serverTimestamp: payload.server_timestamp
    };
  }

  if (payload.type === "ROOM_ENDED") {
    return {
      type: payload.type,
      roomCode: payload.room_code,
      message: payload.message,
      serverTimestamp: payload.server_timestamp
    };
  }

  if (payload.type === "ERROR") {
    return {
      type: payload.type,
      code: payload.code,
      message: payload.message
    };
  }

  return payload;
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
  async getContentPlayback(id) {
    const token = getStoredToken();
    const payload = await apiRequest(`/api/catalog/${id}/playback`, {
      token
    });
    return normalizePlayback(payload);
  },
  async createWatchPartyRoom(payload) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const response = await apiRequest("/api/watch-party/rooms", {
      method: "POST",
      token,
      body: payload
    });
    return normalizeWatchPartyDetail(response);
  },
  async getWatchPartyRoom(roomCode) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const response = await apiRequest(`/api/watch-party/rooms/${roomCode}`, {
      token
    });
    return normalizeWatchPartyDetail(response);
  },
  async joinWatchPartyRoom(roomCode) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const response = await apiRequest(`/api/watch-party/rooms/${roomCode}/join`, {
      method: "POST",
      token
    });
    return normalizeWatchPartyDetail(response);
  },
  async leaveWatchPartyRoom(roomCode) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    await apiRequest(`/api/watch-party/rooms/${roomCode}/leave`, {
      method: "POST",
      token
    });
    return true;
  },
  async endWatchPartyRoom(roomCode) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    await apiRequest(`/api/watch-party/rooms/${roomCode}`, {
      method: "DELETE",
      token
    });
    return true;
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
  async getMyWatchHistory() {
    const token = getStoredToken();
    if (!token) return [];
    const payload = await apiRequest("/api/users/me/history", {
      token
    });
    return (payload || []).map(normalizeWatchHistoryEntry);
  },
  async getMyFavorites() {
    const token = getStoredToken();
    if (!token) return [];
    const payload = await apiRequest("/api/users/me/favorites", {
      token
    });
    return (payload || []).map((item) => String(item.content_id));
  },
  async addMyFavorite(contentId) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    await apiRequest(`/api/users/me/favorites/${encodeURIComponent(String(contentId))}`, {
      method: "POST",
      token
    });
    return true;
  },
  async removeMyFavorite(contentId) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    await apiRequest(`/api/users/me/favorites/${encodeURIComponent(String(contentId))}`, {
      method: "DELETE",
      token
    });
    return true;
  },
  async upsertWatchHistory({
    contentId,
    contentType = "content",
    watchPositionSeconds = 0,
    totalWatchedDurationSeconds = 0,
    isCompleted = false,
    lastWatchedAt = null
  }) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    return apiRequest("/api/users/me/history", {
      method: "POST",
      token,
      body: {
        content_id: contentId,
        content_type: contentType,
        watch_position_seconds: Math.max(0, Math.floor(watchPositionSeconds)),
        total_watched_duration_seconds: Math.max(0, Math.floor(totalWatchedDurationSeconds)),
        is_completed: Boolean(isCompleted),
        last_watched_at: lastWatchedAt
      }
    });
  },
  async generateViewingPlan(payload) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const plan = await apiRequest("/api/viewing-plans/generate", {
      method: "POST",
      token,
      body: payload,
      timeoutMs: 120000
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
  },
  async generateMyChannel(payload) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const plan = await apiRequest("/api/my-channel/generate", {
      method: "POST",
      token,
      body: payload,
      timeoutMs: 120000
    });
    return normalizeViewingPlan(plan);
  },
  async getMyChannelPlans() {
    const token = getStoredToken();
    if (!token) return [];
    const payload = await apiRequest("/api/my-channel", {
      token
    });
    return (payload.items || []).map(normalizeViewingPlan);
  },
  async getMyChannelPlan(planId) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    const payload = await apiRequest(`/api/my-channel/${planId}`, {
      token
    });
    return normalizeViewingPlan(payload);
  },
  async assistantChat(payload) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError("You are not authenticated.", 401);
    }
    return apiRequest("/api/assistant/chat", {
      method: "POST",
      token,
      body: payload
    });
  },
  normalizeWatchPartyEvent(payload) {
    return normalizeWatchPartyEvent(payload);
  }
};
