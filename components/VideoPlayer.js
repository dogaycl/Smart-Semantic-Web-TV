import { mediaBackground } from "./ContentCard.js";

export function VideoPlayer(item) {
  return `
    <section class="video-player">
      <div class="video-screen" style="--hero:${mediaBackground(item, "backdrop")}">
        <div>
          <span class="live-badge">LIVE</span>
          <h1>${item.title}</h1>
          <p class="content-meta">${item.channel} • ${item.duration} • ${item.category}</p>
        </div>
      </div>
      <div class="player-controls">
        <button class="icon-button">▶</button>
        <div class="progress"><span style="width:64%"></span></div>
        <span class="content-meta">21:00 - 22:15</span>
      </div>
    </section>
  `;
}
