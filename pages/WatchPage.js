import { mediaBackground } from "../components/ContentCard.js";
import { mountPlayerAdapter, renderPlaybackSurface } from "../components/playerAdapters.js";
import { api } from "../services/api.js?v=31";
import { startCatalogWatchParty } from "./WatchPartyPage.js";

let activeAdapter = null;
let activeProgressTimer = null;
let activePersistProgress = null;

function cleanupWatchPlayer() {
  window.clearInterval(activeProgressTimer);
  activeProgressTimer = null;
  activeAdapter?.destroy?.();
  activeAdapter = null;
  activePersistProgress = null;
}

function formatClock(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  if (hours) return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatRelative(dateString) {
  if (!dateString) return "Recently";
  const value = new Date(dateString);
  if (Number.isNaN(value.getTime())) return "Recently";
  return value.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function watchProgressPercent(progress, runtimeMinutes) {
  const durationSeconds = Math.max(0, Number(runtimeMinutes || 0) * 60);
  if (!durationSeconds) return 0;
  return Math.max(0, Math.min(100, Math.round((progress / durationSeconds) * 100)));
}

function detailMeta(item, source) {
  return [
    item.year,
    item.duration,
    item.language,
    source?.type ? source.type.toUpperCase() : null
  ].filter(Boolean).join(" • ");
}

function sourceBadge(source) {
  if (!source) return "Unavailable";
  if (source.type === "youtube") return "YouTube";
  if (source.type === "hls") return "HLS";
  if (source.type === "mp4") return "MP4";
  return "Embed";
}

function sourceCapabilitiesLabel(source) {
  if (!source?.capabilities?.canReportProgress) {
    return "Authorized embed playback. Precise progress sync is limited.";
  }
  return "Progress sync and resume are enabled for this source.";
}

function sourceSelector(sources, selectedSourceId) {
  if (!sources.length) return "";
  return `
    <div class="playback-source-row">
      ${sources.map((source) => `
        <button
          class="playback-source-chip ${source.id === selectedSourceId ? "active" : ""}"
          type="button"
          data-playback-source="${source.id}"
        >
          <strong>${sourceBadge(source)}</strong>
          <span>${source.name}</span>
        </button>
      `).join("")}
    </div>
  `;
}

function watchLayout(item, playback, selectedSource) {
  const resumeSeconds = playback.watchProgress?.watchPositionSeconds || 0;
  const resumePercent = watchProgressPercent(resumeSeconds, item.runtimeMinutes);
  const fallbackEmbed = playback.watchAction === "watch_trailer" ? playback.fallback?.embedUrl : null;

  return `
    <section class="watch-shell" style="--watch-hero:${mediaBackground(item, "backdrop")}">
      <section class="watch-stage panel">
        <div class="watch-stage-copy">
          <div>
            <span class="eyebrow">${item.category} • ${item.primaryGenre}</span>
            <h1>${item.title}</h1>
            <p class="detail-meta">${detailMeta(item, selectedSource)}</p>
          </div>
          <div class="watch-actions-inline">
            <a class="ghost-button" href="#/content/${item.slug}">Back to Details</a>
            ${playback.watchAction === "watch_now" ? `<button class="ghost-button" type="button" data-watch-party-button>Watch Together</button>` : ""}
            ${item.trailer?.embedUrl ? `<a class="ghost-button" href="#/content/${item.slug}">Trailer & Metadata</a>` : ""}
          </div>
        </div>

        <div class="watch-player-shell" data-watch-player-shell>
          <div class="watch-player" data-watch-player>
            ${playback.playbackAvailable && selectedSource
              ? renderPlaybackSurface(selectedSource, item.title)
              : fallbackEmbed
                ? `<iframe class="playback-frame" src="${fallbackEmbed}" title="${item.title} trailer" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen loading="lazy"></iframe>`
                : `<div class="playback-empty-state"><strong>Playback unavailable</strong><p>${playback.message}</p></div>`}
          </div>
          <div class="watch-player-meta">
            <div class="watch-player-statusline">
              <span class="channel-source">${playback.playbackAvailable ? sourceBadge(selectedSource) : playback.watchAction === "watch_trailer" ? "Trailer" : "Unavailable"}</span>
              <span class="muted" data-playback-state-label>${playback.playbackAvailable ? "Ready to play" : playback.watchAction === "watch_trailer" ? "Trailer fallback" : "No legal source"}</span>
            </div>
            <div class="watch-progress-rail">
              <span data-watch-progress-bar style="width:${resumePercent}%"></span>
            </div>
            <div class="watch-time-row">
              <strong data-watch-time-label>${formatClock(resumeSeconds)}</strong>
              <span class="muted" data-watch-duration-label>${item.duration || "Duration unknown"}</span>
            </div>
            <p class="muted" data-playback-status>${playback.message}</p>
          </div>
        </div>
      </section>

      ${sourceSelector(playback.sources, selectedSource?.id || null)}

      <section class="story-shell">
        <span class="eyebrow">Playback Details</span>
        <h2>${playback.playbackAvailable ? "Real source connected" : "Playback fallback"}</h2>
        <div class="watch-detail-grid">
          <div>
            <span>Current action</span>
            <strong>${playback.watchAction === "watch_now" ? "Watch Now" : playback.watchAction === "watch_trailer" ? "Watch Trailer" : "Not Available"}</strong>
          </div>
          <div>
            <span>Source provider</span>
            <strong>${selectedSource?.providerName || playback.fallback?.label || "Unavailable"}</strong>
          </div>
          <div>
            <span>Resume point</span>
            <strong>${resumeSeconds ? `${formatClock(resumeSeconds)} (${resumePercent}%)` : "Start from beginning"}</strong>
          </div>
          <div>
            <span>Last activity</span>
            <strong>${playback.watchProgress ? formatRelative(playback.watchProgress.lastWatchedAt) : "No saved progress"}</strong>
          </div>
        </div>
        ${selectedSource ? `
          <div class="credit-list">
            <div>
              <span class="eyebrow">Rights / Source note</span>
              <p>${selectedSource.licenseNote || selectedSource.sourceNote || "Source details unavailable."}</p>
            </div>
            <div>
              <span class="eyebrow">Player capability</span>
              <p>${sourceCapabilitiesLabel(selectedSource)}</p>
            </div>
          </div>
        ` : `
          <div class="credit-list">
            <div>
              <span class="eyebrow">Playback note</span>
              <p>${playback.fallback?.message || playback.message}</p>
            </div>
          </div>
        `}
      </section>
    </section>
  `;
}

export function WatchPage(slug) {
  queueMicrotask(async () => {
    const mount = document.querySelector("#watchMount");
    if (!mount) return;

    cleanupWatchPlayer();

    try {
      const [item, playback] = await Promise.all([
        api.getContentById(slug),
        api.getContentPlayback(slug)
      ]);

      let selectedSourceId = playback.primarySource?.id || playback.sources[0]?.id || null;
      let currentSource = playback.sources.find((source) => source.id === selectedSourceId) || playback.primarySource || null;
      let maxSeenPosition = playback.watchProgress?.watchPositionSeconds || 0;
      let syncInFlight = false;

      const persistProgress = async (force = false) => {
        if (!currentSource?.capabilities?.can_report_progress || !activeAdapter || syncInFlight) return;
        const currentTime = Math.floor(activeAdapter.getCurrentTime?.() || 0);
        const duration = Math.floor(activeAdapter.getDuration?.() || 0);
        maxSeenPosition = Math.max(maxSeenPosition, currentTime);

        if (!force && currentTime < 5) return;
        syncInFlight = true;
        try {
          await api.upsertWatchHistory({
            contentId: item.slug,
            contentType: "content",
            watchPositionSeconds: currentTime,
            totalWatchedDurationSeconds: Math.max(
              playback.watchProgress?.totalWatchedDurationSeconds || 0,
              maxSeenPosition
            ),
            isCompleted: duration > 0 ? currentTime >= Math.max(duration - 15, duration * 0.92) : false,
            lastWatchedAt: new Date().toISOString()
          });
        } catch {
          // Keep playback responsive even if a background progress sync fails once.
        } finally {
          syncInFlight = false;
        }
      };

      activePersistProgress = persistProgress;

      const teardown = () => {
        void persistProgress(true);
        cleanupWatchPlayer();
      };

      window.addEventListener("hashchange", teardown, { once: true });
      window.addEventListener("beforeunload", teardown, { once: true });

      const mountSelectedSource = async () => {
        cleanupWatchPlayer();
        currentSource = playback.sources.find((source) => source.id === selectedSourceId) || playback.primarySource || null;
        mount.innerHTML = watchLayout(item, playback, currentSource);

        document.querySelectorAll("[data-playback-source]").forEach((button) => {
          button.addEventListener("click", async () => {
            const nextId = Number(button.dataset.playbackSource || 0);
            if (!nextId || nextId === selectedSourceId) return;
            await persistProgress(true);
            selectedSourceId = nextId;
            await mountSelectedSource();
          });
        });

        document.querySelector("[data-watch-party-button]")?.addEventListener("click", async () => {
          const statusLabel = document.querySelector("[data-playback-status]");
          const button = document.querySelector("[data-watch-party-button]");
          button.disabled = true;
          statusLabel.textContent = "Creating a watch room...";
          try {
            await persistProgress(true);
            await startCatalogWatchParty(item.slug);
          } catch (error) {
            statusLabel.textContent = error.message || "The watch room could not be created.";
            button.disabled = false;
          }
        });

        if (!playback.playbackAvailable || !currentSource) return;

        const playerRoot = document.querySelector("[data-watch-player]");
        const progressBar = document.querySelector("[data-watch-progress-bar]");
        const timeLabel = document.querySelector("[data-watch-time-label]");
        const durationLabel = document.querySelector("[data-watch-duration-label]");
        const stateLabel = document.querySelector("[data-playback-state-label]");
        const statusLabel = document.querySelector("[data-playback-status]");

        activeAdapter = await mountPlayerAdapter({
          source: currentSource,
          root: playerRoot,
          onStateChange: ({ state, currentTime, duration }) => {
            const percent = duration > 0 ? Math.max(0, Math.min(100, (currentTime / duration) * 100)) : watchProgressPercent(currentTime, item.runtimeMinutes);
            progressBar.style.width = `${percent}%`;
            timeLabel.textContent = formatClock(currentTime);
            durationLabel.textContent = duration > 0 ? formatClock(duration) : (item.duration || "Duration unknown");
            stateLabel.textContent = state === "playing"
              ? "Playing"
              : state === "paused"
                ? "Paused"
                : state === "ended"
                  ? "Completed"
                  : state === "loading"
                    ? "Loading"
                    : "Ready";

            if (state === "playing" && currentSource.capabilities?.can_report_progress) {
              window.clearInterval(activeProgressTimer);
              activeProgressTimer = window.setInterval(() => {
                void persistProgress(false);
              }, 15000);
            }

            if ((state === "paused" || state === "ended") && currentSource.capabilities?.can_report_progress) {
              window.clearInterval(activeProgressTimer);
              activeProgressTimer = null;
              void persistProgress(true);
            }
          },
          onError: (message) => {
            statusLabel.textContent = message;
            stateLabel.textContent = "Playback error";
          }
        });

        if (currentSource.capabilities?.can_seek && playback.watchProgress?.watchPositionSeconds) {
          window.setTimeout(() => {
            activeAdapter?.seek?.(playback.watchProgress.watchPositionSeconds);
          }, 600);
        }

        if (currentSource.capabilities?.can_play) {
          await activeAdapter?.play?.();
        }

        if (!currentSource.capabilities?.can_report_progress) {
          statusLabel.textContent = `${playback.message} Exact watch-progress sync is limited for this source type.`;
        }
      };

      await mountSelectedSource();
    } catch (error) {
      mount.innerHTML = `
        <section class="story-shell">
          <div class="empty-state">${error.message || "Playback could not be loaded."}</div>
        </section>
      `;
    }
  });

  return `
    <main class="page">
      <div id="watchMount">
        <section class="story-shell">
          <div class="empty-state">Loading playback...</div>
        </section>
      </div>
    </main>
  `;
}
