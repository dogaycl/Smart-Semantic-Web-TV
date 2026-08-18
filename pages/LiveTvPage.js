import { api } from "../services/api.js";
import { VideoPlayer, cleanupVideoPlayer, mountVideoPlayer } from "../components/VideoPlayer.js?v=22";
import { ChannelList } from "../components/ChannelList.js?v=23";
import { EPGGuide } from "../components/EPGGuide.js?v=25";
import { startChannelWatchParty } from "./WatchPartyPage.js";

const LIVE_TV_FILTERS = ["All", "News", "Sports", "Music", "Entertainment", "Youth", "Documentary", "Technology", "Business", "Education", "General TV"];
const LIVE_TV_LANGUAGE_FILTERS = [
  { label: "All", code: null },
  { label: "Turkish", code: "tr" },
  { label: "English", code: "en" }
];
const PREFERRED_LIVE_CHANNELS = [
  "TRT Haber",
  "Bloomberg TV",
  "Euronews English",
  "TRT World",
  "Arirang TV",
  "Yahoo! Finance",
  "Cloudflare TV",
  "NatureTime",
  "FITE 24/7",
  "Bloomberg Originals"
];

let liveTvRequestId = 0;

function renderPlayerMessage(badge, title, message) {
  return `
    <section class="video-player">
      <div class="video-screen live-empty-state">
        <div class="live-fallback">
          <span class="live-badge">${badge}</span>
          <h1>${title}</h1>
          <p class="content-meta">${message}</p>
        </div>
      </div>
    </section>
  `;
}

function annotateChannels(data) {
  const guideByChannelId = new Map((data.epg?.channels || []).map((item) => [item.channel.id, item.entries || []]));
  return (data.channels || []).map((channel) => {
    const entries = guideByChannelId.get(channel.id) || [];
    return {
      ...channel,
      guide_entries: entries.length,
      has_schedule: entries.length > 0
    };
  });
}

function visibleFilters(channels) {
  const categories = new Set(channels.map((channel) => channel.category).filter(Boolean));
  return LIVE_TV_FILTERS.filter((filter) => filter === "All" || categories.has(filter));
}

function visibleLanguageFilters(channels) {
  const languages = new Set(channels.map((channel) => (channel.language || "").toLowerCase()).filter(Boolean));
  return LIVE_TV_LANGUAGE_FILTERS.filter((filter) => filter.code === null || languages.has(filter.code));
}

function filterChannels(channels, activeFilter, activeLanguage) {
  return channels.filter((channel) => {
    const matchesCategory = activeFilter === "All" || channel.category === activeFilter;
    const matchesLanguage = !activeLanguage || (channel.language || "").toLowerCase() === activeLanguage;
    return matchesCategory && matchesLanguage;
  });
}

function filterEpg(epg, visibleChannelIds) {
  return {
    ...epg,
    channels: (epg?.channels || []).filter(({ channel }) => visibleChannelIds.has(channel.id))
  };
}

function preferredPlayableChannel(channels) {
  for (const name of PREFERRED_LIVE_CHANNELS) {
    const match = channels.find((channel) => channel.name === name && channel.playback.type !== "unavailable");
    if (match) return match;
  }
  return channels.find((channel) => channel.playback.type !== "unavailable") || channels[0] || null;
}

function renderFilters(activeFilter, activeLanguage, channels) {
  const languageFilters = visibleLanguageFilters(channels);
  return `
    <div class="filter-bar" aria-label="Live TV category filters">
      ${visibleFilters(channels).map((filter) => `
        <button class="chip ${filter === activeFilter ? "active" : ""}" data-live-filter="${filter}" type="button">${filter}</button>
      `).join("")}
    </div>
    ${languageFilters.length > 1 ? `
      <div class="filter-bar" aria-label="Live TV language filters">
        ${languageFilters.map((filter) => `
          <button class="chip ${filter.code === activeLanguage ? "active" : ""}" data-live-language-filter="${filter.code || ""}" type="button">${filter.label}</button>
        `).join("")}
      </div>
    ` : ""}
  `;
}

function renderWatchPartyAction(channel) {
  if (!channel || channel.playback.type === "unavailable") {
    return `
      <section class="panel page-panel watch-party-inline-card">
        <div>
          <span class="eyebrow">Watch Party</span>
          <h2>Unavailable for this channel</h2>
          <p class="muted">Choose a playable live source to open a synchronized room with chat.</p>
        </div>
      </section>
    `;
  }

  return `
    <section class="panel page-panel watch-party-inline-card">
      <div>
        <span class="eyebrow">Watch Party</span>
        <h2>Watch ${channel.name} together</h2>
        <p class="muted">Create a host-controlled room with real-time chat for this live source.</p>
      </div>
      <button class="primary-button" type="button" data-live-watch-party="${channel.id}">Watch Together</button>
    </section>
  `;
}

export function LiveTvPage() {
  queueMicrotask(async () => {
    const requestId = ++liveTvRequestId;
    const page = document.querySelector("[data-live-tv-page]");
    if (!page) return;

    window.addEventListener("hashchange", cleanupVideoPlayer, { once: true });
    document.querySelector("#livePlayer").innerHTML = renderPlayerMessage(
      "Loading",
      "Connecting to live sources",
      "Fetching curated Turkish and English channels, stream health, and real EPG data."
    );

    try {
      const payload = await api.getLiveTv();
      if (requestId !== liveTvRequestId) return;

      let channels = annotateChannels(payload);
      const epg = payload.epg;
      let activeFilter = "All";
      let activeLanguage = null;
      const failedChannelIds = new Set();

      if (!channels.length) {
        document.querySelector("#liveFilters").innerHTML = "";
        document.querySelector("#livePlayer").innerHTML = renderPlayerMessage(
          "Empty",
          "No live channels configured",
          "Run the live TV sync and try again."
        );
        document.querySelector("#liveChannels").innerHTML = ChannelList([]);
        document.querySelector("#epgMount").innerHTML = EPGGuide(epg, null);
        return;
      }

      const preferredChannelId = Number(sessionStorage.getItem("synapse.live.channel-id") || 0);
      sessionStorage.removeItem("synapse.live.channel-id");
      let selectedChannelId = channels.find((channel) => channel.id === preferredChannelId)?.id
        || preferredPlayableChannel(channels)?.id
        || channels[0].id;

      const assistantContext = page.querySelector("[data-assistant-context]");

      const loadChannel = async (channelId) => {
        const baseChannel = channels.find((channel) => channel.id === channelId);
        if (!baseChannel) return null;
        const liveChannel = await api.getChannelLive(channelId).catch(() => null);
        return liveChannel ? { ...baseChannel, ...liveChannel } : baseChannel;
      };

      const render = async ({ refreshSelected = false } = {}) => {
        document.querySelector("#liveFilters").innerHTML = renderFilters(activeFilter, activeLanguage, channels);
        let visibleChannels = filterChannels(channels, activeFilter, activeLanguage);

        if (!visibleChannels.length) {
          assistantContext?.removeAttribute("data-channel-id");
          assistantContext?.removeAttribute("data-epg-entry-id");
          assistantContext?.setAttribute("data-context-type", "channel");
          assistantContext?.setAttribute("data-context-label", "Live TV");
          document.dispatchEvent(new CustomEvent("assistant:context-changed"));
          document.querySelector("#livePlayer").innerHTML = renderPlayerMessage(
            "Filtered",
            "No channels matched this filter",
            "Choose another category or language to browse the curated live TV catalog."
          );
          document.querySelector("#liveChannels").innerHTML = ChannelList([]);
          document.querySelector("#epgMount").innerHTML = EPGGuide({ ...epg, channels: [] }, null);
          bindFilterButtons(render);
          return;
        }

        if (!visibleChannels.some((channel) => channel.id === selectedChannelId)) {
          selectedChannelId = preferredPlayableChannel(visibleChannels)?.id || visibleChannels[0].id;
          refreshSelected = true;
        }

        let selectedChannel = channels.find((channel) => channel.id === selectedChannelId);
        if (!selectedChannel) return;

        if (refreshSelected) {
          const refreshed = await loadChannel(selectedChannelId);
          if (refreshed) {
            channels = channels.map((channel) => (channel.id === refreshed.id ? refreshed : channel));
            selectedChannel = refreshed;
            visibleChannels = filterChannels(channels, activeFilter, activeLanguage);
          }
        }

        const visibleIds = new Set(visibleChannels.map((channel) => channel.id));
        const filteredEpg = filterEpg(epg, visibleIds);
        const tryNextChannel = async (message) => {
          failedChannelIds.add(selectedChannel.id);
          const nextChannel = visibleChannels.find((channel) => (
            channel.id !== selectedChannel.id
            && channel.playback.type !== "unavailable"
            && !failedChannelIds.has(channel.id)
          ));
          const prioritizedFallback = preferredPlayableChannel(
            visibleChannels.filter((channel) => channel.id !== selectedChannel.id && !failedChannelIds.has(channel.id))
          );

          const fallbackChannel = prioritizedFallback || nextChannel;

          if (!fallbackChannel) {
            const statusMount = document.querySelector("[data-live-player-status]");
            if (statusMount) {
              statusMount.textContent = message || "No fallback live channel is currently available.";
            }
            return;
          }

          const statusMount = document.querySelector("[data-live-player-status]");
          if (statusMount) {
            statusMount.textContent = `Switching to ${fallbackChannel.name}...`;
          }
          selectedChannelId = fallbackChannel.id;
          await render({ refreshSelected: true });
        };

        assistantContext?.setAttribute("data-context-type", selectedChannel.current_program?.id ? "program" : "channel");
        assistantContext?.setAttribute("data-channel-id", String(selectedChannel.id));
        assistantContext?.setAttribute(
          "data-context-label",
          selectedChannel.current_program?.title
            ? `${selectedChannel.current_program.title} on ${selectedChannel.name}`
            : selectedChannel.name
        );
        if (selectedChannel.current_program?.id) {
          assistantContext?.setAttribute("data-epg-entry-id", String(selectedChannel.current_program.id));
        } else {
          assistantContext?.removeAttribute("data-epg-entry-id");
        }
        document.dispatchEvent(new CustomEvent("assistant:context-changed"));

        document.querySelector("#livePlayer").innerHTML = VideoPlayer(selectedChannel);
        document.querySelector("#liveWatchPartyActions").innerHTML = renderWatchPartyAction(selectedChannel);
        document.querySelector("#liveChannels").innerHTML = ChannelList(visibleChannels, selectedChannel.id);
        document.querySelector("#epgMount").innerHTML = EPGGuide(filteredEpg, selectedChannel.id);
        await mountVideoPlayer(selectedChannel, {
          onPlaybackFailure: async (message) => {
            await tryNextChannel(message);
          }
        }).catch(async () => {
          await tryNextChannel("This live stream could not be loaded.");
        });

        document.querySelector("[data-live-watch-party]")?.addEventListener("click", async (event) => {
          const button = event.currentTarget;
          button.disabled = true;
          button.textContent = "Creating room...";
          try {
            await startChannelWatchParty(selectedChannel.id);
          } catch (error) {
            button.disabled = false;
            button.textContent = error.message || "Watch Together";
          }
        });

        document.querySelectorAll("[data-channel-id]").forEach((button) => {
          button.addEventListener("click", async () => {
            const channelId = Number(button.dataset.channelId);
            if (!channelId || channelId === selectedChannelId) return;
            selectedChannelId = channelId;
            await render({ refreshSelected: true });
          });
        });

        bindFilterButtons(render);
      };

      const bindFilterButtons = (renderPage) => {
        document.querySelectorAll("[data-live-filter]").forEach((button) => {
          button.addEventListener("click", async () => {
            const nextFilter = button.dataset.liveFilter || "All";
            if (nextFilter === activeFilter) return;
            activeFilter = nextFilter;
            await renderPage({ refreshSelected: false });
          });
        });
        document.querySelectorAll("[data-live-language-filter]").forEach((button) => {
          button.addEventListener("click", async () => {
            const nextLanguage = button.dataset.liveLanguageFilter || null;
            if (nextLanguage === activeLanguage) return;
            activeLanguage = nextLanguage;
            await renderPage({ refreshSelected: false });
          });
        });
      };

      await render({ refreshSelected: true });
    } catch (error) {
      cleanupVideoPlayer();
      document.querySelector("#liveFilters").innerHTML = "";
      document.querySelector("#livePlayer").innerHTML = renderPlayerMessage(
        "Error",
        "Live TV could not be loaded",
        error.message || "Check backend sync and external source availability."
      );
      document.querySelector("#liveChannels").innerHTML = "";
      document.querySelector("#epgMount").innerHTML = "";
    }
  });

  return `
    <main class="page" data-live-tv-page>
      <div hidden data-assistant-context></div>
      <div class="section-head"><div><span class="eyebrow">Curated Turkish &amp; English Live TV</span><h1 class="page-title">Live TV</h1></div></div>
      <div id="liveFilters"></div>
      <section class="live-layout">
        <div id="livePlayer"></div>
        <div id="liveChannels" class="live-channels-slot"></div>
      </section>
      <div id="epgMount"></div>
      <div id="liveWatchPartyActions"></div>
    </main>
  `;
}
