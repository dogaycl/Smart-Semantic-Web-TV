import { api } from "../services/api.js?v=55";
import { VideoPlayer, cleanupVideoPlayer, mountVideoPlayer } from "../components/VideoPlayer.js?v=55";
import { ChannelList } from "../components/ChannelList.js?v=55";
import {
  EPGGuide,
  captureEPGScroll,
  cleanupEPGGuide,
  dayKeyOf,
  mountEPGGuide
} from "../components/EPGGuide.js?v=55";
import { startChannelWatchParty } from "./WatchPartyPage.js";

const LIVE_TV_FILTERS = ["All", "News", "Sports", "Music", "Entertainment", "Youth", "Documentary", "Technology", "Business", "Education", "General TV"];
const LIVE_TV_LANGUAGE_FILTERS = [
  { label: "All", code: null },
  { label: "Turkish", code: "tr" },
  { label: "English", code: "en" }
];
const PREFERRED_LIVE_CHANNELS = [
  "TRT 1",
  "Show TV",
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

const TURKISH_COUNTRY_CODES = new Set(["TR", "TUR"]);

function channelPriority(channel) {
  const name = String(channel.name || "").trim();
  const normalizedName = name.toLocaleLowerCase("tr-TR");
  const isTurkish = TURKISH_COUNTRY_CODES.has(String(channel.country || "").toUpperCase())
    || String(channel.language || "").toLowerCase() === "tr";
  if (normalizedName === "trt 1") return 0;
  if (normalizedName === "show tv") return 1;
  if (normalizedName.startsWith("trt ")) return 2;
  if (isTurkish) return 3;
  return 4;
}

function sortChannels(channels) {
  return [...channels].sort((a, b) => (
    channelPriority(a) - channelPriority(b)
    || String(a.name || "").localeCompare(String(b.name || ""), "tr", { sensitivity: "base" })
  ));
}

let liveTvRequestId = 0;

function pad(value) {
  return String(value).padStart(2, "0");
}

function todayDateValue() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function startOfDay(date) {
  const value = new Date(date);
  value.setHours(0, 0, 0, 0);
  return value;
}

function addDays(date, amount) {
  const value = new Date(date);
  // Adding calendar days rather than 24h keeps day boundaries exact across DST changes.
  value.setDate(value.getDate() + amount);
  return value;
}

// The guide always shows one full local day, so Prev/Next boundaries are exact and each day
// can be cached under a simple key. "Today" still shows earlier programmes; the viewport just
// opens scrolled to the current time.
function epgDayWindow(date) {
  const start = startOfDay(date);
  return { start, end: addDays(start, 1) };
}

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
  return sortChannels((data.channels || []).map((channel) => {
    const entries = guideByChannelId.get(channel.id) || [];
    return {
      ...channel,
      guide_entries: entries.length,
      has_schedule: entries.length > 0
    };
  }));
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
  const order = new Map(channelsForEpgOrder(epg, visibleChannelIds).map((id, index) => [id, index]));
  return {
    ...epg,
    channels: (epg?.channels || [])
      .filter(({ channel }) => visibleChannelIds.has(channel.id))
      .sort((a, b) => (order.get(a.channel.id) ?? 9999) - (order.get(b.channel.id) ?? 9999))
  };
}

function channelsForEpgOrder(epg, visibleChannelIds) {
  return sortChannels((epg?.channels || []).map(({ channel }) => channel))
    .filter((channel) => visibleChannelIds.has(channel.id))
    .map((channel) => channel.id);
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
    window.addEventListener("hashchange", cleanupEPGGuide, { once: true });
    document.querySelector("#livePlayer").innerHTML = renderPlayerMessage(
      "Loading",
      "Connecting to live sources",
      "Fetching curated Turkish and English channels, stream health, and real EPG data."
    );

    try {
      let selectedDate = startOfDay(new Date());
      const initialWindow = epgDayWindow(selectedDate);
      // An expired token would otherwise reject the whole Promise.all and blank the page.
      const [payload, initialPlan] = await Promise.all([
        api.getLiveTv({ start: initialWindow.start, end: initialWindow.end, slotMinutes: 30 }),
        api.getActiveMyChannelPlan(dayKeyOf(selectedDate)).catch(() => null)
      ]);
      if (requestId !== liveTvRequestId) return;

      let acceptedPlan = initialPlan;
      let channels = annotateChannels(payload);
      let epg = payload.epg;
      const epgCache = new Map([[dayKeyOf(selectedDate), payload.epg]]);
      const planCache = new Map([[dayKeyOf(selectedDate), initialPlan]]);
      let epgRequestId = 0;
      let epgLoading = false;
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
        document.querySelector("#epgMount").innerHTML = EPGGuide({ epg, selectedDate, activePlan: acceptedPlan });
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

      // Rendering the guide is separate from render(): a date change must not re-mount the video
      // player, which would interrupt playback.
      const renderEpg = () => {
        const mount = document.querySelector("#epgMount");
        if (!mount) return;
        const visibleIds = new Set(filterChannels(channels, activeFilter, activeLanguage).map((channel) => channel.id));
        captureEPGScroll(mount);
        mount.innerHTML = EPGGuide({
          epg: filterEpg(epg, visibleIds),
          selectedChannelId,
          activePlan: acceptedPlan,
          selectedDate,
          loading: epgLoading
        });
        mountEPGGuide(mount, {
          onSelectDate: (token) => {
            if (token === "today") return loadEpgForDate(startOfDay(new Date()));
            if (token === "-1" || token === "1") return loadEpgForDate(addDays(selectedDate, Number(token)));
            const parsed = new Date(`${token}T00:00:00`);
            if (!Number.isNaN(parsed.getTime())) return loadEpgForDate(startOfDay(parsed));
            return undefined;
          },
          // Clicking a programme block opens that channel in the player (details are in the
          // hover tooltip, there is no separate detail panel).
          onSelectChannel: async (channelId) => {
            if (!channelId || channelId === selectedChannelId) return;
            selectedChannelId = channelId;
            await render({ refreshSelected: true });
          }
        });
      };

      const loadEpgForDate = async (date) => {
        const currentRequest = ++epgRequestId;
        selectedDate = date;
        const key = dayKeyOf(date);

        if (epgCache.has(key)) {
          epg = epgCache.get(key);
          acceptedPlan = planCache.get(key) ?? null;
          epgLoading = false;
          renderEpg();
          return;
        }

        epgLoading = true;
        renderEpg();
        const window_ = epgDayWindow(date);
        const [nextEpg, nextPlan] = await Promise.all([
          api.getEpgWindow({ start: window_.start, end: window_.end, slotMinutes: 30 }).catch(() => null),
          api.getActiveMyChannelPlan(key).catch(() => null)
        ]);
        if (currentRequest !== epgRequestId) return;

        epgLoading = false;
        if (nextEpg) {
          epgCache.set(key, nextEpg);
          epg = nextEpg;
        }
        planCache.set(key, nextPlan);
        acceptedPlan = nextPlan;
        renderEpg();
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
          renderEpg();
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
        renderEpg();
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

        // Scoped to the channel list: this selector is document-wide, and the hidden
        // [data-assistant-context] element also carries data-channel-id.
        document.querySelectorAll("#liveChannels [data-channel-id]").forEach((button) => {
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
