import { api } from "../services/api.js";
import { content } from "../data/mockData.js";
import { VideoPlayer } from "../components/VideoPlayer.js";
import { ChannelList } from "../components/ChannelList.js";
import { EPGGuide } from "../components/EPGGuide.js";

export function LiveTvPage() {
  queueMicrotask(async () => {
    const data = await api.getLiveTv();
    document.querySelector("#liveChannels").innerHTML = ChannelList(data.channels);
    document.querySelector("#epgMount").innerHTML = EPGGuide(data.channels, data.epgSlots, data.epgPrograms);
  });

  return `
    <main class="page">
      <div class="section-head"><div><span class="eyebrow">Plex-style Live TV</span><h1 class="page-title">Live TV</h1></div></div>
      <section class="live-layout">
        ${VideoPlayer(content[3])}
        <div id="liveChannels"></div>
      </section>
      <div id="epgMount"></div>
    </main>
  `;
}
