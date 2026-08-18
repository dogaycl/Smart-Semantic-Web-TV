let hlsScriptPromise = null;
let youTubeApiPromise = null;

function loadHlsScript() {
  if (window.Hls) return Promise.resolve(window.Hls);
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

function loadYouTubeApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (youTubeApiPromise) return youTubeApiPromise;

  youTubeApiPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[src="https://www.youtube.com/iframe_api"]');
    const previousHandler = window.onYouTubeIframeAPIReady;

    window.onYouTubeIframeAPIReady = () => {
      previousHandler?.();
      resolve(window.YT);
    };

    if (!existing) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      script.async = true;
      script.onerror = () => reject(new Error("Failed to load YouTube player API."));
      document.head.appendChild(script);
    }

    window.setTimeout(() => {
      if (!window.YT?.Player) {
        reject(new Error("YouTube player API did not finish loading in time."));
      }
    }, 10000);
  });

  return youTubeApiPromise;
}

class BasePlayerAdapter {
  constructor(source, { onStateChange, onError } = {}) {
    this.source = source;
    this.onStateChange = onStateChange;
    this.onError = onError;
    this.state = "idle";
  }

  async load() {}

  async play() {}

  pause() {}

  seek() {}

  getCurrentTime() {
    return 0;
  }

  getDuration() {
    return 0;
  }

  getPlaybackState() {
    return this.state;
  }

  destroy() {}

  emit(extra = {}) {
    this.onStateChange?.({
      state: this.getPlaybackState(),
      currentTime: this.getCurrentTime(),
      duration: this.getDuration(),
      sourceType: this.source?.type,
      ...extra
    });
  }

  fail(message) {
    this.state = "error";
    this.onError?.(message);
    this.emit({ error: message });
  }
}

class Html5PlayerAdapter extends BasePlayerAdapter {
  constructor(video, source, handlers = {}) {
    super(source, handlers);
    this.video = video;
    this.listeners = [];
  }

  async load() {
    this.bindEvents();
    this.video.src = this.source.playbackUrl || "";
    this.video.preload = "metadata";
    this.video.playsInline = true;
    this.state = "ready";
    this.emit();
  }

  bindEvents() {
    const events = {
      loadedmetadata: () => this.emit(),
      timeupdate: () => this.emit(),
      play: () => {
        this.state = "playing";
        this.emit();
      },
      pause: () => {
        if (this.video.ended) return;
        this.state = "paused";
        this.emit();
      },
      ended: () => {
        this.state = "ended";
        this.emit();
      },
      error: () => {
        this.fail("This video could not be played in your browser.");
      }
    };

    Object.entries(events).forEach(([eventName, handler]) => {
      this.video.addEventListener(eventName, handler);
      this.listeners.push([eventName, handler]);
    });
  }

  async play() {
    try {
      await this.video.play();
    } catch {}
  }

  pause() {
    this.video.pause();
  }

  seek(seconds) {
    if (!Number.isFinite(seconds)) return;
    try {
      this.video.currentTime = Math.max(0, seconds);
      this.emit();
    } catch {}
  }

  getCurrentTime() {
    return Number.isFinite(this.video.currentTime) ? this.video.currentTime : 0;
  }

  getDuration() {
    return Number.isFinite(this.video.duration) ? this.video.duration : 0;
  }

  destroy() {
    this.pause();
    this.listeners.forEach(([eventName, handler]) => {
      this.video.removeEventListener(eventName, handler);
    });
    this.listeners = [];
    this.video.removeAttribute("src");
    this.video.load();
  }
}

class HlsPlayerAdapter extends Html5PlayerAdapter {
  constructor(video, source, handlers = {}) {
    super(video, source, handlers);
    this.hls = null;
  }

  async load() {
    this.bindEvents();
    if (this.video.canPlayType("application/vnd.apple.mpegurl")) {
      this.video.src = this.source.playbackUrl || "";
      this.state = "ready";
      this.emit();
      return;
    }

    const Hls = await loadHlsScript();
    if (!Hls?.isSupported()) {
      this.fail("Your browser does not support HLS playback.");
      return;
    }

    this.hls = new Hls();
    this.hls.loadSource(this.source.playbackUrl);
    this.hls.attachMedia(this.video);
    this.hls.on(Hls.Events.MANIFEST_PARSED, () => {
      this.state = "ready";
      this.emit();
    });
    this.hls.on(Hls.Events.ERROR, (_, data) => {
      if (data?.fatal) {
        this.fail("The HLS stream could not be loaded.");
      }
    });
  }

  destroy() {
    this.hls?.destroy();
    this.hls = null;
    super.destroy();
  }
}

class YouTubePlayerAdapter extends BasePlayerAdapter {
  constructor(container, source, handlers = {}) {
    super(source, handlers);
    this.container = container;
    this.player = null;
    this.progressTimer = null;
  }

  async load() {
    const YT = await loadYouTubeApi();
    this.state = "loading";
    this.emit();

    await new Promise((resolve) => {
      this.player = new YT.Player(this.container, {
        videoId: this.source.externalVideoId,
        playerVars: {
          autoplay: 0,
          rel: 0,
          playsinline: 1,
          modestbranding: 1,
          origin: window.location.origin
        },
        events: {
          onReady: () => {
            this.state = "ready";
            this.emit();
            resolve();
          },
          onStateChange: (event) => {
            this.state = mapYouTubeState(event.data);
            this.toggleTicker(this.state === "playing");
            this.emit();
          },
          onError: () => {
            this.fail("The YouTube player could not load this video.");
          }
        }
      });
    });
  }

  toggleTicker(shouldRun) {
    window.clearInterval(this.progressTimer);
    this.progressTimer = null;
    if (!shouldRun) return;
    this.progressTimer = window.setInterval(() => this.emit(), 1000);
  }

  async play() {
    this.player?.playVideo?.();
  }

  pause() {
    this.player?.pauseVideo?.();
  }

  seek(seconds) {
    if (!Number.isFinite(seconds)) return;
    this.player?.seekTo?.(Math.max(0, seconds), true);
    this.emit();
  }

  getCurrentTime() {
    return Number(this.player?.getCurrentTime?.() || 0);
  }

  getDuration() {
    return Number(this.player?.getDuration?.() || 0);
  }

  destroy() {
    window.clearInterval(this.progressTimer);
    this.progressTimer = null;
    this.player?.destroy?.();
    this.player = null;
  }
}

class ExternalPlayerAdapter extends BasePlayerAdapter {
  constructor(iframe, source, handlers = {}) {
    super(source, handlers);
    this.iframe = iframe;
  }

  async load() {
    this.state = "ready";
    this.emit();
  }
}

function mapYouTubeState(state) {
  if (!window.YT?.PlayerState) return "idle";
  switch (state) {
    case window.YT.PlayerState.PLAYING:
      return "playing";
    case window.YT.PlayerState.PAUSED:
      return "paused";
    case window.YT.PlayerState.ENDED:
      return "ended";
    case window.YT.PlayerState.BUFFERING:
      return "loading";
    case window.YT.PlayerState.CUED:
      return "ready";
    default:
      return "idle";
  }
}

export function renderPlaybackSurface(source, title) {
  if (!source) {
    return `
      <div class="playback-empty-state">
        <strong>Playback unavailable</strong>
        <p>No legal source is currently configured for ${title}.</p>
      </div>
    `;
  }

  if (source.type === "youtube") {
    return `<div class="playback-frame" data-youtube-player aria-label="${title} player"></div>`;
  }

  if (source.type === "external") {
    return `
      <iframe
        class="playback-frame"
        src="${source.embedUrl || source.playbackUrl}"
        title="${title} player"
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
        allowfullscreen
        loading="lazy"
      ></iframe>
    `;
  }

  return `<video class="playback-frame playback-video" controls playsinline preload="metadata"></video>`;
}

export async function mountPlayerAdapter({ source, root, onStateChange, onError }) {
  if (!root || !source) return null;

  let adapter = null;
  if (source.type === "hls") {
    adapter = new HlsPlayerAdapter(root.querySelector("video"), source, { onStateChange, onError });
  } else if (source.type === "mp4") {
    adapter = new Html5PlayerAdapter(root.querySelector("video"), source, { onStateChange, onError });
  } else if (source.type === "youtube") {
    adapter = new YouTubePlayerAdapter(root.querySelector("[data-youtube-player]"), source, { onStateChange, onError });
  } else if (source.type === "external") {
    adapter = new ExternalPlayerAdapter(root.querySelector("iframe"), source, { onStateChange, onError });
  }

  await adapter?.load();
  return adapter;
}
