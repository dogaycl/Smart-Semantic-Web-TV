import { api } from "../services/api.js";
import { VideoPlayer, cleanupVideoPlayer, mountVideoPlayer } from "../components/VideoPlayer.js";
import { ChannelList } from "../components/ChannelList.js";
import { EPGGuide } from "../components/EPGGuide.js";

let liveTvRequestId = 0;

export function LiveTvPage() {
  queueMicrotask(async () => {
    const requestId = ++liveTvRequestId;
    const page = document.querySelector("[data-live-tv-page]");
    if (!page) return;

    window.addEventListener("hashchange", cleanupVideoPlayer, { once: true });
    document.querySelector("#livePlayer").innerHTML = `
      <section class="video-player">
        <div class="video-screen live-empty-state">
          <div class="live-fallback">
            <span class="live-badge">Loading</span>
            <h1>Connecting to live sources</h1>
            <p class="content-meta">Fetching channels, stream health, and real EPG data.</p>
          </div>
        </div>
      </section>
    `;

    try {
      const data = await api.getLiveTv();
      if (requestId !== liveTvRequestId) return;

      if (!data.channels.length) {
        document.querySelector("#livePlayer").innerHTML = `
          <section class="video-player">
            <div class="video-screen live-empty-state">
              <div class="live-fallback">
                <span class="live-badge">Empty</span>
                <h1>No live channels configured</h1>
                <p class="content-meta">Sync channels and try again.</p>
              </div>
            </div>
          </section>
        `;
        document.querySelector("#liveChannels").innerHTML = ChannelList([]);
        document.querySelector("#epgMount").innerHTML = EPGGuide(data.epg, null);
        return;
      }

      const preferredChannelId = Number(sessionStorage.getItem("synapse.live.channel-id") || 0);
      sessionStorage.removeItem("synapse.live.channel-id");
      let selectedChannel = data.channels.find((channel) => channel.id === preferredChannelId && channel.playback.type !== "unavailable")
        || data.channels.find((channel) => channel.playback.type !== "unavailable")
        || data.channels[0];
      selectedChannel = await api.getChannelLive(selectedChannel.id).catch(() => selectedChannel);

      const render = async (channel) => {
        const mergedChannels = data.channels.map((item) => (item.id === channel.id ? { ...item, ...channel } : item));
        document.querySelector("#livePlayer").innerHTML = VideoPlayer(channel);
        document.querySelector("#liveChannels").innerHTML = ChannelList(mergedChannels, channel.id);
        document.querySelector("#epgMount").innerHTML = EPGGuide(data.epg, channel.id);
        await mountVideoPlayer(channel).catch(() => {});
        document.querySelectorAll("[data-channel-id]").forEach((button) => {
          button.addEventListener("click", async () => {
            const channelId = Number(button.dataset.channelId);
            const nextChannel = await api.getChannelLive(channelId).catch(() => mergedChannels.find((item) => item.id === channelId));
            if (!nextChannel) return;
            await render(nextChannel);
          });
        });
      };

      await render(selectedChannel);
    } catch (error) {
      cleanupVideoPlayer();
      document.querySelector("#livePlayer").innerHTML = `
        <section class="video-player">
          <div class="video-screen live-empty-state">
            <div class="live-fallback">
              <span class="live-badge">Error</span>
              <h1>Live TV could not be loaded</h1>
              <p class="content-meta">${error.message || "Check backend sync and external source availability."}</p>
            </div>
          </div>
        </section>
      `;
      document.querySelector("#liveChannels").innerHTML = "";
      document.querySelector("#epgMount").innerHTML = "";
    }
  });

  return `
    <main class="page" data-live-tv-page>
      <div class="section-head"><div><span class="eyebrow">Plex-style Live TV</span><h1 class="page-title">Live TV</h1></div></div>
      <section class="live-layout">
        <div id="livePlayer"></div>
        <div id="liveChannels"></div>
      </section>
      <div id="epgMount"></div>
    </main>
  `;
}
