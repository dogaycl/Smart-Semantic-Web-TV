import { mediaBackground } from "./ContentCard.js";

let hlsScriptPromise = null;
let hlsInstance = null;
let playbackTimeoutId = null;

function playerTitle(channel) {
  return channel.current_program?.title || channel.live_title || channel.name;
}

function playerTimeLabel(channel) {
  if (channel.current_program) {
    return `${new Date(channel.current_program.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - ${new Date(channel.current_program.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  if (channel.scheduled_start_time) {
    const start = new Date(channel.scheduled_start_time);
    const end = channel.scheduled_end_time ? new Date(channel.scheduled_end_time) : null;
    return `${start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}${end ? ` - ${end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}`;
  }
  return "Live status updates on refresh";
}

function playerMeta(channel) {
  const parts = [channel.name];
  if (channel.category) parts.push(channel.category);
  if (channel.country) parts.push(channel.country);
  return parts.join(" • ");
}

export function VideoPlayer(channel) {
  const background = channel.thumbnail_url
    ? `url('${channel.thumbnail_url}')`
    : mediaBackground({ image: channel.logo_url, backdrop: channel.logo_url }, "backdrop");

  const unavailableMessage = channel.stream_error || channel.live_description || "This channel is currently unavailable.";

  return `
    <section class="video-player">
      <div class="video-screen" style="--hero:${background}">
        ${channel.playback.type === "youtube" ? `
          <iframe
            class="live-embed"
            src="${channel.playback.embed_url}"
            title="${playerTitle(channel)}"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowfullscreen
          ></iframe>
        ` : channel.playback.type === "hls" ? `
          <video class="live-embed live-video-element" data-live-video controls playsinline preload="metadata"></video>
        ` : `
          <div class="live-fallback">
            <span class="live-badge">Unavailable</span>
            <h1>${channel.name}</h1>
            <p class="content-meta">${unavailableMessage}</p>
          </div>
        `}
        <div class="video-overlay">
          <span class="live-badge">${channel.live_status === "upcoming" ? "Upcoming" : channel.live_status === "live" ? "Live" : "Source"}</span>
          <h1>${playerTitle(channel)}</h1>
          <p class="content-meta">${playerMeta(channel)}</p>
        </div>
      </div>
      <div class="player-controls">
        <span class="channel-source">${channel.source_type === "youtube" ? "YouTube embed" : "Direct HLS stream"}</span>
        <div class="progress"><span style="width:${channel.live_status === "live" ? "100%" : channel.live_status === "upcoming" ? "36%" : "8%"}"></span></div>
        <span class="content-meta">${playerTimeLabel(channel)}</span>
        <span class="content-meta live-player-note" data-live-player-status>${channel.stream_error || ""}</span>
      </div>
    </section>
  `;
}

export function cleanupVideoPlayer() {
  window.clearTimeout(playbackTimeoutId);
  playbackTimeoutId = null;
  if (hlsInstance) {
    hlsInstance.destroy();
    hlsInstance = null;
  }
}

async function loadHlsScript() {
  if (window.Hls) return window.Hls;
  if (hlsScriptPromise) return hlsScriptPromise;

  hlsScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js";
    script.async = true;
    script.onload = () => resolve(window.Hls);
    script.onerror = () => reject(new Error("Failed to load HLS player library."));
    document.head.appendChild(script);
  });

  return hlsScriptPromise;
}

export async function mountVideoPlayer(channel, { onPlaybackFailure } = {}) {
  cleanupVideoPlayer();

  if (channel.playback.type !== "hls" || !channel.playback.stream_url) return;

  const video = document.querySelector("[data-live-video]");
  const status = document.querySelector("[data-live-player-status]");
  if (!video) return;

  const failPlayback = (message) => {
    if (status) status.textContent = message;
    onPlaybackFailure?.(message);
  };

  const markPlayable = () => {
    window.clearTimeout(playbackTimeoutId);
    playbackTimeoutId = null;
    if (status && !status.textContent.startsWith("Switching")) {
      status.textContent = "";
    }
  };

  video.addEventListener("loadedmetadata", markPlayable, { once: true });
  video.addEventListener("playing", markPlayable, { once: true });
  video.addEventListener("error", () => {
    failPlayback("This live stream stopped responding in the browser.");
  }, { once: true });

  playbackTimeoutId = window.setTimeout(() => {
    if ((video.readyState || 0) < 2) {
      failPlayback("This channel is taking too long to start.");
    }
  }, 12000);

  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = channel.playback.stream_url;
    await video.play().catch(() => {});
    return;
  }

  const Hls = await loadHlsScript();
  if (!Hls?.isSupported()) {
    failPlayback("Your browser does not support HLS playback.");
    return;
  }

  hlsInstance = new Hls();
  hlsInstance.loadSource(channel.playback.stream_url);
  hlsInstance.attachMedia(video);
  hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
    video.play().catch(() => {});
  });
  hlsInstance.on(Hls.Events.ERROR, (_, data) => {
    if (data?.fatal) {
      failPlayback("The live stream could not be played in this browser.");
    }
  });
}
