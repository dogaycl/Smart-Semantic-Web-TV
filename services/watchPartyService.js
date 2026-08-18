import { API_BASE_URL, api } from "./api.js";
import { getAccessToken } from "../contexts/authContext.js";

function socketBaseUrl() {
  return API_BASE_URL.replace(/^http/i, "ws");
}

export function buildWatchPartyInviteUrl(invitePath) {
  return `${window.location.origin}${window.location.pathname}${invitePath}`;
}

export function buildWatchPartySocketUrl(roomCode) {
  const token = getAccessToken();
  if (!token) {
    throw new Error("You are not authenticated.");
  }
  return `${socketBaseUrl()}/api/watch-party/ws/${encodeURIComponent(roomCode)}?token=${encodeURIComponent(token)}`;
}

export async function createCatalogWatchParty(contentSlug) {
  return api.createWatchPartyRoom({
    target_type: "catalog",
    content_slug: contentSlug
  });
}

export async function createChannelWatchParty(channelId) {
  return api.createWatchPartyRoom({
    target_type: "channel",
    channel_id: channelId
  });
}

export async function ensureJoinedWatchParty(roomCode) {
  const detail = await api.getWatchPartyRoom(roomCode);
  if (detail.joined) return detail;
  return api.joinWatchPartyRoom(roomCode);
}

export class WatchPartyConnection {
  constructor(roomCode, handlers = {}) {
    this.roomCode = roomCode;
    this.handlers = handlers;
    this.socket = null;
    this.closedByClient = false;
  }

  connect() {
    this.closedByClient = false;
    const socket = new WebSocket(buildWatchPartySocketUrl(this.roomCode));
    this.socket = socket;

    socket.addEventListener("open", () => {
      this.handlers.onOpen?.();
    });

    socket.addEventListener("message", (event) => {
      try {
        const parsed = JSON.parse(event.data);
        this.handlers.onMessage?.(api.normalizeWatchPartyEvent(parsed));
      } catch {
        this.handlers.onError?.(new Error("The watch room sent an unreadable message."));
      }
    });

    socket.addEventListener("close", (event) => {
      this.handlers.onClose?.({
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
        closedByClient: this.closedByClient
      });
    });

    socket.addEventListener("error", () => {
      this.handlers.onError?.(new Error("The watch room connection failed."));
    });
  }

  send(payload) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify(payload));
    return true;
  }

  close(code = 1000, reason = "Leaving room") {
    this.closedByClient = true;
    this.socket?.close(code, reason);
  }
}
