import { mediaBackground } from "../components/ContentCard.js";
import { logout } from "../contexts/authContext.js";
import { mountPlayerAdapter, renderPlaybackSurface } from "../components/playerAdapters.js";
import { api, ApiError } from "../services/api.js";
import {
  WatchPartyConnection,
  buildWatchPartyInviteUrl,
  createCatalogWatchParty,
  createChannelWatchParty,
  ensureJoinedWatchParty
} from "../services/watchPartyService.js";

let activePartyCleanup = null;

function cleanupWatchPartyPage() {
  activePartyCleanup?.();
  activePartyCleanup = null;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatClock(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  if (hours) return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatTimestamp(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Just now";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatRelative(value) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unavailable";
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function backPathForTarget(target) {
  return target.targetType === "catalog"
    ? `#/content/${target.contentSlug}`
    : "#/live-tv";
}

function channelPlaybackSource(channel, target) {
  if (!channel?.playback || channel.playback.type === "unavailable") return null;
  return {
    id: `channel-${channel.id}`,
    name: channel.name,
    type: channel.playback.type,
    playbackUrl: channel.playback.stream_url || null,
    embedUrl: channel.playback.embed_url || null,
    externalVideoId: channel.playback.youtube_video_id || channel.youtube_video_id || null,
    quality: channel.quality || null,
    providerName: channel.source_type === "youtube" ? "YouTube Live" : "Public HLS Stream",
    providerUrl: null,
    licenseNote: null,
    sourceNote: target.subtitle || "Live playback is synchronized to the active room state.",
    capabilities: {
      can_play: true,
      can_pause: true,
      can_seek: false,
      can_report_progress: false,
      can_fullscreen: true,
      supports_seek: false,
      supports_state_tracking: true
    }
  };
}

async function loadTargetPlayback(target) {
  if (target.targetType === "catalog") {
    const [item, playback] = await Promise.all([
      api.getContentById(target.contentSlug),
      api.getContentPlayback(target.contentSlug)
    ]);

    return {
      kind: "catalog",
      title: item.title,
      subtitle: [item.category, item.primaryGenre, item.year].filter(Boolean).join(" • "),
      hero: mediaBackground(item, "backdrop"),
      meta: item,
      playback,
      source: playback.primarySource || playback.sources[0] || null,
      historyTarget: {
        contentId: item.slug,
        contentType: "content",
        durationHintSeconds: Math.max(0, Number(item.runtimeMinutes || 0) * 60)
      }
    };
  }

  const channel = await api.getChannelLive(target.channelId);
  return {
    kind: "channel",
    title: channel.current_program?.title || channel.live_title || target.title,
    subtitle: [target.subtitle, channel.name].filter(Boolean).join(" • "),
    hero: target.backdropUrl ? `url('${target.backdropUrl}')` : "linear-gradient(135deg, #090b10, #141823, #23180d)",
    meta: channel,
    playback: null,
    source: channelPlaybackSource(channel, target),
    historyTarget: channel.current_program
      ? {
          contentId: String(channel.current_program.id),
          contentType: "program",
          durationHintSeconds: Math.max(
            0,
            Math.floor((new Date(channel.current_program.end_time) - new Date(channel.current_program.start_time)) / 1000)
          )
        }
      : null
  };
}

function roomStatusLabel(state) {
  if (state.roomDetail.room.status === "ended") return "Ended";
  if (state.connectionState === "connected") return state.roomDetail.role === "host" ? "Host connected" : "Following host";
  if (state.connectionState === "reconnecting") return "Reconnecting";
  if (state.connectionState === "error") return "Connection issue";
  return "Connecting";
}

function playbackStatusLabel(state) {
  if (state.roomDetail.room.status === "ended") return "Room ended";
  if (state.roomDetail.room.playbackState === "playing") return "Playing together";
  if (state.roomDetail.room.playbackState === "paused") return "Paused";
  if (state.roomDetail.room.playbackState === "ended") return "Playback ended";
  return "Ready";
}

function renderParticipants(participants = []) {
  if (!participants.length) {
    return `<div class="empty-state compact">No participants yet.</div>`;
  }

  const ordered = [...participants].sort((left, right) => {
    if (left.isHost !== right.isHost) return left.isHost ? -1 : 1;
    if (left.isConnected !== right.isConnected) return left.isConnected ? -1 : 1;
    return left.displayName.localeCompare(right.displayName);
  });

  return `
    <div class="watch-party-participants">
      ${ordered.map((participant) => `
        <div class="watch-party-user">
          <span class="watch-party-avatar">${escapeHtml((participant.displayName || participant.username).slice(0, 2).toUpperCase())}</span>
          <div>
            <strong>${escapeHtml(participant.displayName)}</strong>
            <small class="muted">${participant.isHost ? "Host" : "Participant"} • ${participant.isConnected ? "Connected" : "Disconnected"}</small>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function renderChat(messages = []) {
  if (!messages.length) {
    return `<div class="empty-state compact">Send the first message to start the room chat.</div>`;
  }

  return `
    <div class="watch-party-chat-list">
      ${messages.slice(-30).map((message) => `
        <article class="watch-party-chat-item">
          <div class="watch-party-chat-head">
            <strong>${escapeHtml(message.displayName)}</strong>
            <span>${formatTimestamp(message.createdAt)}</span>
          </div>
          <p>${escapeHtml(message.messageText)}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function watchPartyLayout(state) {
  const target = state.roomDetail.target;
  const source = state.targetPlayback.source;
  const backPath = backPathForTarget(target);
  const inviteUrl = buildWatchPartyInviteUrl(state.roomDetail.invitePath);
  const showCreateFollowup = target.targetType === "catalog" && target.contentSlug;

  return `
    <section class="watch-shell watch-party-shell">
      <section class="watch-stage panel watch-party-stage" style="--watch-hero:${state.targetPlayback.hero}">
        <div class="watch-stage-copy">
          <div>
            <span class="eyebrow">Watch Party • ${escapeHtml(target.targetType === "catalog" ? "On-Demand" : "Live TV")}</span>
            <h1>${escapeHtml(state.targetPlayback.title || target.title)}</h1>
            <p class="detail-meta">${escapeHtml(state.targetPlayback.subtitle || target.subtitle || "")}</p>
          </div>
          <div class="watch-actions-inline">
            <a class="ghost-button" href="${backPath}">Back</a>
            ${showCreateFollowup ? `<button class="ghost-button" type="button" data-room-new-copy>Create another room</button>` : ""}
            <button class="ghost-button" type="button" data-room-copy>Copy invite link</button>
            <button class="primary-button" type="button" data-room-leave>${state.roomDetail.role === "host" ? "End Room" : "Leave Room"}</button>
          </div>
        </div>

        <div class="watch-party-layout">
          <div class="watch-party-main">
            <div class="watch-player-shell">
              <div class="watch-player" data-watch-party-player>
                ${source
                  ? renderPlaybackSurface(source, state.targetPlayback.title || target.title)
                  : `<div class="playback-empty-state"><strong>Playback unavailable</strong><p>This room target is no longer playable.</p></div>`}
              </div>
              <div class="watch-player-meta">
                <div class="watch-player-statusline">
                  <span class="channel-source">${escapeHtml(state.roomDetail.role === "host" ? "Host-controlled room" : "Participant sync mode")}</span>
                  <span class="muted" data-room-connection-state>${escapeHtml(roomStatusLabel(state))}</span>
                </div>
                <div class="watch-progress-rail">
                  <span data-room-progress-bar style="width:0%"></span>
                </div>
                <div class="watch-time-row">
                  <strong data-room-time-label>${formatClock(state.roomDetail.room.authoritativePosition)}</strong>
                  <span class="muted" data-room-duration-label>${escapeHtml(state.targetPlayback.meta?.duration || (target.targetType === "channel" ? "Live broadcast" : "Duration unavailable"))}</span>
                </div>
                <p class="muted" data-room-playback-status>${escapeHtml(state.notice || playbackStatusLabel(state))}</p>
              </div>
            </div>
          </div>

          <aside class="panel page-panel watch-party-sidebar">
            <div class="watch-party-room-card">
              <div>
                <span class="eyebrow">Room Code</span>
                <h2>${escapeHtml(state.roomDetail.room.roomCode)}</h2>
              </div>
              <div class="watch-party-pill-row">
                <span class="watch-party-pill">${escapeHtml(playbackStatusLabel(state))}</span>
                <span class="watch-party-pill subtle">${escapeHtml(source?.type ? source.type.toUpperCase() : "N/A")}</span>
              </div>
              <p class="muted">Invite link</p>
              <div class="watch-party-invite-line">
                <code data-room-invite-url>${escapeHtml(inviteUrl)}</code>
              </div>
              <p class="muted" data-room-sync-copy>${state.roomDetail.role === "host"
                ? "Your play, pause, and seek actions drive the room."
                : `The host controls playback. Drift above ${state.driftThresholdSeconds.toFixed(1)}s will be corrected.`}</p>
              <button class="ghost-button" type="button" data-room-sync-now>Sync now</button>
            </div>

            <div class="watch-party-panel">
              <div class="section-head">
                <h2>Participants</h2>
                <span class="muted" data-room-participant-count>${state.roomDetail.participants.length} connected</span>
              </div>
              <div data-room-participants>${renderParticipants(state.roomDetail.participants)}</div>
            </div>

            <div class="watch-party-panel">
              <div class="section-head">
                <h2>Chat</h2>
                <span class="muted" data-room-chat-count>${state.roomDetail.recentMessages.length} messages</span>
              </div>
              <div data-room-chat>${renderChat(state.roomDetail.recentMessages)}</div>
              <form class="watch-party-chat-form" data-room-chat-form>
                <input class="input" data-room-chat-input maxlength="400" placeholder="Write a message..." ${state.roomDetail.room.status === "ended" ? "disabled" : ""} />
                <button class="primary-button" ${state.roomDetail.room.status === "ended" ? "disabled" : ""}>Send</button>
              </form>
            </div>
          </aside>
        </div>
      </section>
    </section>
  `;
}

export function WatchPartyPage(roomCode) {
  queueMicrotask(async () => {
    const mount = document.querySelector("#watchPartyMount");
    if (!mount) return;

    cleanupWatchPartyPage();

    let destroyed = false;
    let reconnectTimer = null;
    let syncTimer = null;
    let progressTimer = null;
    let activeAdapter = null;
    let activeConnection = null;
    let activeSource = null;
    let localSnapshot = {
      state: null,
      currentTime: 0,
      duration: 0,
      observedAt: Date.now()
    };
    let lastOutbound = {
      type: null,
      position: null,
      sentAt: 0
    };
    let ignoreRemoteUntil = 0;
    let syncInFlight = false;
    let maxSeenPosition = 0;
    let state = {
      roomDetail: null,
      targetPlayback: null,
      connectionState: "connecting",
      driftThresholdSeconds: 1.5,
      notice: ""
    };

    const cleanup = () => {
      if (destroyed) return;
      destroyed = true;
      window.clearTimeout(reconnectTimer);
      window.clearInterval(syncTimer);
      window.clearInterval(progressTimer);
      activeConnection?.close(1000, "Route changed");
      activeConnection = null;
      activeAdapter?.destroy?.();
      activeAdapter = null;
    };

    activePartyCleanup = cleanup;
    window.addEventListener("hashchange", cleanup, { once: true });
    window.addEventListener("beforeunload", cleanup, { once: true });

    const updateParticipantsMount = () => {
      const participantsMount = document.querySelector("[data-room-participants]");
      const countMount = document.querySelector("[data-room-participant-count]");
      if (!participantsMount || !state.roomDetail) return;
      participantsMount.innerHTML = renderParticipants(state.roomDetail.participants);
      countMount.textContent = `${state.roomDetail.participants.filter((item) => item.isConnected).length} connected`;
    };

    const updateChatMount = () => {
      const chatMount = document.querySelector("[data-room-chat]");
      const countMount = document.querySelector("[data-room-chat-count]");
      if (!chatMount || !state.roomDetail) return;
      chatMount.innerHTML = renderChat(state.roomDetail.recentMessages);
      chatMount.scrollTop = chatMount.scrollHeight;
      if (countMount) {
        countMount.textContent = `${state.roomDetail.recentMessages.length} messages`;
      }
    };

    const updatePlayerMeta = ({ stateLabel = null, currentTime = null, duration = null, status = null } = {}) => {
      const connectionMount = document.querySelector("[data-room-connection-state]");
      const progressBar = document.querySelector("[data-room-progress-bar]");
      const timeMount = document.querySelector("[data-room-time-label]");
      const durationMount = document.querySelector("[data-room-duration-label]");
      const statusMount = document.querySelector("[data-room-playback-status]");
      const syncCopyMount = document.querySelector("[data-room-sync-copy]");

      if (connectionMount) connectionMount.textContent = roomStatusLabel(state);
      if (timeMount) timeMount.textContent = formatClock(currentTime ?? state.roomDetail?.room.authoritativePosition ?? 0);
      if (durationMount) {
        durationMount.textContent = duration && duration > 0
          ? formatClock(duration)
          : state.targetPlayback?.meta?.duration || (state.roomDetail?.target.targetType === "channel" ? "Live broadcast" : "Duration unavailable");
      }
      if (statusMount) statusMount.textContent = status || state.notice || stateLabel || playbackStatusLabel(state);
      if (syncCopyMount) {
        syncCopyMount.textContent = state.roomDetail?.role === "host"
          ? "Your play, pause, and seek actions drive the room."
          : `The host controls playback. Drift above ${state.driftThresholdSeconds.toFixed(1)}s will be corrected.`;
      }

      const durationHint = duration
        || state.targetPlayback?.historyTarget?.durationHintSeconds
        || localSnapshot.duration
        || 0;
      const progressBase = durationHint > 0
        ? Math.max(0, Math.min(100, ((currentTime ?? localSnapshot.currentTime) / durationHint) * 100))
        : 0;
      if (progressBar) progressBar.style.width = `${progressBase}%`;
    };

    const persistProgress = async (force = false) => {
      const historyTarget = state.targetPlayback?.historyTarget;
      if (!historyTarget || !activeSource?.capabilities?.can_report_progress || !activeAdapter || syncInFlight) return;
      const currentTime = Math.floor(activeAdapter.getCurrentTime?.() || 0);
      const duration = Math.floor(activeAdapter.getDuration?.() || historyTarget.durationHintSeconds || 0);
      maxSeenPosition = Math.max(maxSeenPosition, currentTime);
      if (!force && currentTime < 5) return;

      syncInFlight = true;
      try {
        await api.upsertWatchHistory({
          contentId: historyTarget.contentId,
          contentType: historyTarget.contentType,
          watchPositionSeconds: currentTime,
          totalWatchedDurationSeconds: maxSeenPosition,
          isCompleted: duration > 0 ? currentTime >= Math.max(duration - 15, duration * 0.92) : false,
          lastWatchedAt: new Date().toISOString()
        });
      } catch {
        // Keep the room responsive even if a background watch-history sync fails.
      } finally {
        syncInFlight = false;
      }
    };

    const rememberOutbound = (type, position = null) => {
      lastOutbound = {
        type,
        position,
        sentAt: Date.now()
      };
    };

    const shouldDeduplicate = (type, position = null) => {
      if (lastOutbound.type !== type) return false;
      if (Date.now() - lastOutbound.sentAt > 1000) return false;
      if (position == null || lastOutbound.position == null) return true;
      return Math.abs(lastOutbound.position - position) < 0.8;
    };

    const sendRoomEvent = (payload) => {
      if (!activeConnection?.send(payload)) return false;
      rememberOutbound(payload.type, payload.position ?? null);
      return true;
    };

    const setRemoteGuard = (durationMs = 1200) => {
      ignoreRemoteUntil = Date.now() + durationMs;
    };

    const isApplyingRemoteEvent = () => Date.now() < ignoreRemoteUntil;

    const syncPlayerToRoom = async ({ playbackState, authoritativePosition, forceSeek = false, driftThreshold = null } = {}) => {
      if (!activeAdapter || !activeSource) return;
      const threshold = driftThreshold ?? state.driftThresholdSeconds;
      const currentTime = Number(activeAdapter.getCurrentTime?.() || 0);
      const shouldSeek = Boolean(activeSource.capabilities?.can_seek) && (forceSeek || Math.abs(currentTime - authoritativePosition) > threshold);

      setRemoteGuard();

      if (shouldSeek) {
        activeAdapter.seek?.(Math.max(0, authoritativePosition));
      }

      if (playbackState === "playing") {
        await activeAdapter.play?.();
      } else if (playbackState === "paused") {
        activeAdapter.pause?.();
      }

      updatePlayerMeta({
        stateLabel: playbackState === "playing" ? "Playing together" : playbackState === "paused" ? "Paused by host" : "Synchronized",
        currentTime: authoritativePosition
      });
    };

    const mergeParticipant = (participant) => {
      const current = state.roomDetail.participants || [];
      const next = [...current];
      const index = next.findIndex((entry) => entry.userId === participant.userId);
      if (index >= 0) {
        next[index] = { ...next[index], ...participant };
      } else {
        next.push(participant);
      }
      state.roomDetail.participants = next;
    };

    const bindShellEvents = () => {
      document.querySelector("[data-room-copy]")?.addEventListener("click", async () => {
        const inviteUrl = buildWatchPartyInviteUrl(state.roomDetail.invitePath);
        try {
          await navigator.clipboard.writeText(inviteUrl);
          state.notice = "Invite link copied to clipboard.";
        } catch {
          state.notice = "Copy failed. You can still share the room URL shown in the sidebar.";
        }
        updatePlayerMeta();
      });

      document.querySelector("[data-room-new-copy]")?.addEventListener("click", async () => {
        try {
          const detail = await createCatalogWatchParty(state.roomDetail.target.contentSlug);
          location.hash = `/watch-party/${detail.room.roomCode}`;
        } catch (error) {
          state.notice = error.message || "A new watch room could not be created.";
          updatePlayerMeta();
        }
      });

      document.querySelector("[data-room-sync-now]")?.addEventListener("click", () => {
        activeConnection?.send({ type: "SYNC_REQUEST" });
      });

      document.querySelector("[data-room-leave]")?.addEventListener("click", async () => {
        const backPath = backPathForTarget(state.roomDetail.target);
        try {
          if (state.roomDetail.role === "host") {
            await api.endWatchPartyRoom(state.roomDetail.room.roomCode);
          } else {
            await api.leaveWatchPartyRoom(state.roomDetail.room.roomCode);
          }
        } catch {
          // Socket teardown still happens on navigation even if the REST request fails once.
        } finally {
          cleanup();
          location.hash = backPath.replace(/^#/, "");
        }
      });

      document.querySelector("[data-room-chat-form]")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = document.querySelector("[data-room-chat-input]");
        const message = input?.value.trim();
        if (!message) return;
        if (!sendRoomEvent({ type: "CHAT_MESSAGE", message })) {
          state.notice = "The room is reconnecting. Your message was not sent.";
          updatePlayerMeta();
          return;
        }
        input.value = "";
      });
    };

    const mountPlayer = async () => {
      const playerRoot = document.querySelector("[data-watch-party-player]");
      if (!playerRoot) return;
      activeAdapter?.destroy?.();
      activeAdapter = null;
      activeSource = state.targetPlayback.source;
      maxSeenPosition = state.targetPlayback.playback?.watchProgress?.watchPositionSeconds || 0;
      localSnapshot = {
        state: null,
        currentTime: 0,
        duration: 0,
        observedAt: Date.now()
      };

      if (!activeSource) {
        updatePlayerMeta({ status: "This room target is no longer playable." });
        return;
      }

      activeAdapter = await mountPlayerAdapter({
        source: activeSource,
        root: playerRoot,
        onStateChange: ({ state: nextState, currentTime, duration }) => {
          const now = Date.now();
          const previous = { ...localSnapshot };
          localSnapshot = {
            state: nextState,
            currentTime,
            duration,
            observedAt: now
          };
          updatePlayerMeta({
            stateLabel: nextState === "playing"
              ? "Playing together"
              : nextState === "paused"
                ? "Paused"
                : nextState === "loading"
                  ? "Buffering"
                  : nextState === "ended"
                    ? "Playback ended"
                    : "Ready",
            currentTime,
            duration
          });

          if (activeSource.capabilities?.can_report_progress && nextState === "playing") {
            window.clearInterval(progressTimer);
            progressTimer = window.setInterval(() => {
              void persistProgress(false);
            }, 15000);
          }

          if (activeSource.capabilities?.can_report_progress && (nextState === "paused" || nextState === "ended")) {
            window.clearInterval(progressTimer);
            progressTimer = null;
            void persistProgress(true);
          }

          if (state.roomDetail.role !== "host" || isApplyingRemoteEvent() || state.roomDetail.room.status !== "active") {
            return;
          }

          if (nextState === "playing" && previous.state !== "playing" && !shouldDeduplicate("PLAY", currentTime)) {
            sendRoomEvent({ type: "PLAY", position: currentTime });
            return;
          }

          if ((nextState === "paused" || nextState === "ended") && previous.state === "playing" && !shouldDeduplicate("PAUSE", currentTime)) {
            sendRoomEvent({ type: "PAUSE", position: currentTime });
            return;
          }

          if (activeSource.capabilities?.can_seek && previous.state) {
            const elapsed = Math.max(0, (now - previous.observedAt) / 1000);
            const actualDelta = currentTime - previous.currentTime;
            const expectedDelta = previous.state === "playing" ? elapsed : 0;
            const looksLikeSeek = Math.abs(actualDelta - expectedDelta) > Math.max(2.5, state.driftThresholdSeconds + 0.75);
            if (looksLikeSeek && !shouldDeduplicate("SEEK", currentTime)) {
              sendRoomEvent({ type: "SEEK", position: currentTime });
            }
          }
        },
        onError: (message) => {
          state.notice = message;
          updatePlayerMeta({ status: message });
        }
      });

      const resumePoint = state.targetPlayback.playback?.watchProgress?.watchPositionSeconds || state.roomDetail.room.authoritativePosition || 0;
      if (activeSource.capabilities?.can_seek && resumePoint) {
        setRemoteGuard();
        window.setTimeout(() => {
          activeAdapter?.seek?.(resumePoint);
        }, 500);
      }

      await syncPlayerToRoom({
        playbackState: state.roomDetail.room.playbackState,
        authoritativePosition: state.roomDetail.room.authoritativePosition,
        forceSeek: Boolean(resumePoint)
      });

      if (
        state.roomDetail.role === "host"
        && activeSource.capabilities?.can_seek
        && resumePoint > 0
        && state.roomDetail.room.authoritativePosition < 1
      ) {
        window.setTimeout(() => {
          if (!destroyed) {
            sendRoomEvent({ type: "SEEK", position: resumePoint });
          }
        }, 1400);
      }
    };

    const renderScene = async () => {
      mount.innerHTML = watchPartyLayout(state);
      bindShellEvents();
      updateParticipantsMount();
      updateChatMount();
      updatePlayerMeta();
      await mountPlayer();
    };

    const reconnect = () => {
      if (destroyed || state.roomDetail?.room.status === "ended") return;
      activeConnection = new WatchPartyConnection(roomCode, {
        onOpen: () => {
          state.connectionState = "connected";
          state.notice = "";
          updatePlayerMeta();
        },
        onError: (error) => {
          state.connectionState = "error";
          state.notice = error.message || "The room connection failed.";
          updatePlayerMeta();
        },
        onClose: ({ code, reason, closedByClient }) => {
          if (closedByClient || destroyed) return;
          if (code === 4002 || code === 4401 || code === 4403 || code === 4404 || code === 4409) {
            state.connectionState = "error";
            state.notice = reason || "The room connection closed.";
            if (code === 4401) {
              logout();
              location.hash = "/login";
              return;
            }
            if (code === 4002 || code === 4409) {
              state.roomDetail.room.status = "ended";
            }
            updatePlayerMeta();
            return;
          }

          state.connectionState = "reconnecting";
          state.notice = reason || "Trying to reconnect to the room...";
          updatePlayerMeta();
          window.clearTimeout(reconnectTimer);
          reconnectTimer = window.setTimeout(() => {
            reconnect();
          }, 1500);
        },
        onMessage: async (event) => {
          if (!event || destroyed) return;

          if (event.type === "ROOM_STATE") {
            state.roomDetail.room = event.room;
            state.roomDetail.target = event.target;
            state.roomDetail.participants = event.participants;
            state.roomDetail.recentMessages = event.recentMessages;
            state.driftThresholdSeconds = event.driftThresholdSeconds || state.driftThresholdSeconds;
            updateParticipantsMount();
            updateChatMount();
            await syncPlayerToRoom({
              playbackState: event.room.playbackState,
              authoritativePosition: event.room.authoritativePosition,
              forceSeek: true,
              driftThreshold: event.driftThresholdSeconds
            });
            return;
          }

          if (event.type === "USER_JOINED") {
            mergeParticipant({ ...event.participant, isConnected: true });
            updateParticipantsMount();
            return;
          }

          if (event.type === "USER_LEFT") {
            mergeParticipant({ ...event.participant, isConnected: false });
            updateParticipantsMount();
            return;
          }

          if (event.type === "CHAT_MESSAGE") {
            state.roomDetail.recentMessages = [...state.roomDetail.recentMessages, event.message].slice(-30);
            updateChatMount();
            return;
          }

          if (event.type === "SYNC_STATE") {
            state.roomDetail.room.playbackState = event.playbackState;
            state.roomDetail.room.authoritativePosition = event.authoritativePosition;
            state.driftThresholdSeconds = event.driftThresholdSeconds || state.driftThresholdSeconds;
            await syncPlayerToRoom({
              playbackState: event.playbackState,
              authoritativePosition: event.authoritativePosition,
              driftThreshold: event.driftThresholdSeconds
            });
            return;
          }

          if (event.type === "PLAY" || event.type === "PAUSE" || event.type === "SEEK") {
            state.roomDetail.room.playbackState = event.playbackState;
            state.roomDetail.room.authoritativePosition = event.authoritativePosition;
            if (event.participant) mergeParticipant({ ...event.participant, isConnected: true });
            updateParticipantsMount();
            await syncPlayerToRoom({
              playbackState: event.playbackState,
              authoritativePosition: event.authoritativePosition,
              forceSeek: event.type === "SEEK"
            });
            return;
          }

          if (event.type === "CONTENT_CHANGE" && event.target) {
            state.roomDetail.target = event.target;
            state.roomDetail.room.playbackState = event.playbackState;
            state.roomDetail.room.authoritativePosition = event.authoritativePosition;
            state.targetPlayback = await loadTargetPlayback(event.target);
            await renderScene();
            return;
          }

          if (event.type === "ROOM_ENDED") {
            state.roomDetail.room.status = "ended";
            state.connectionState = "error";
            state.notice = event.message;
            window.clearInterval(syncTimer);
            syncTimer = null;
            updatePlayerMeta({ status: event.message });
            document.querySelector("[data-room-chat-input]")?.setAttribute("disabled", "disabled");
            document.querySelector("[data-room-chat-form] button")?.setAttribute("disabled", "disabled");
            return;
          }

          if (event.type === "ERROR") {
            state.notice = event.message;
            updatePlayerMeta({ status: event.message });
          }
        }
      });
      activeConnection.connect();
    };

    try {
      state.roomDetail = await ensureJoinedWatchParty(roomCode);
      state.targetPlayback = await loadTargetPlayback(state.roomDetail.target);
      state.driftThresholdSeconds = 1.5;
      await renderScene();
      reconnect();

      syncTimer = window.setInterval(() => {
        if (state.roomDetail.role !== "host" && state.roomDetail.room.status === "active") {
          activeConnection?.send({ type: "SYNC_REQUEST" });
        }
      }, 6000);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        logout();
        location.hash = "/login";
        return;
      }

      mount.innerHTML = `
        <section class="story-shell">
          <div class="empty-state">${escapeHtml(error.message || "The watch room could not be loaded.")}</div>
        </section>
      `;
    }
  });

  return `
    <main class="page">
      <div id="watchPartyMount">
        <section class="story-shell">
          <div class="empty-state">Joining watch room...</div>
        </section>
      </div>
    </main>
  `;
}

export async function startCatalogWatchParty(slug) {
  const detail = await createCatalogWatchParty(slug);
  location.hash = `/watch-party/${detail.room.roomCode}`;
}

export async function startChannelWatchParty(channelId) {
  const detail = await createChannelWatchParty(channelId);
  location.hash = `/watch-party/${detail.room.roomCode}`;
}
