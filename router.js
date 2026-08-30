import { getCurrentUser, initializeAuth, isAuthReady } from "./contexts/authContext.js";
import { AppLayout } from "./components/AppLayout.js?v=25";
import { ensureFavoritesLoaded } from "./services/favoritesService.js?v=21";
import { LoginPage } from "./pages/LoginPage.js";
import { RegisterPage } from "./pages/RegisterPage.js";
import { HomePage } from "./pages/HomePage.js?v=23";
import { LiveTvPage } from "./pages/LiveTvPage.js?v=27";
import { LibraryPage } from "./pages/LibraryPage.js?v=26";
import { OnDemandPage } from "./pages/OnDemandPage.js";
import { DiscoverPage } from "./pages/DiscoverPage.js";
import { ContentDetailPage } from "./pages/ContentDetailPage.js?v=23";
import { WatchPage } from "./pages/WatchPage.js";
import { WatchPartyPage } from "./pages/WatchPartyPage.js";
import { MyListPage } from "./pages/MyListPage.js?v=23";
import { ProfilePage } from "./pages/ProfilePage.js";
import { ProfilesPage } from "./pages/ProfilesPage.js";
import { StatsPage } from "./pages/StatsPage.js";
import { AdminPage } from "./pages/AdminPage.js";
import { SocialPage } from "./pages/SocialPage.js";
import { HistoryPage } from "./pages/HistoryPage.js";
import { MyChannelPage } from "./pages/MyChannelPage.js?v=28";
import { AITuningPage } from "./pages/AITuningPage.js";

const routes = [
  { path: "/login", public: true, render: LoginPage },
  { path: "/register", public: true, render: RegisterPage },
  { path: "/", render: HomePage },
  { path: "/live-tv", render: LiveTvPage },
  { path: "/on-demand", render: OnDemandPage },
  { path: "/movies", render: () => LibraryPage("Movies") },
  { path: "/series", render: () => LibraryPage("Series") },
  { path: "/discover", render: DiscoverPage },
  { path: "/my-channel", render: MyChannelPage },
  { path: "/ai", render: MyChannelPage },
  { path: "/ai-tuning", render: AITuningPage },
  { path: "/my-list", render: MyListPage },
  { path: "/history", render: HistoryPage },
  { path: "/profiles", render: ProfilesPage },
  { path: "/stats", render: StatsPage },
  { path: "/social", render: SocialPage },
  { path: "/admin", render: AdminPage },
  { path: "/profile", render: ProfilePage },
  { path: "/settings", render: ProfilePage }
];

function resolveRoute() {
  const hashPath = location.hash.replace("#", "") || "/";
  if (hashPath.startsWith("/watch/")) {
    return { public: false, render: () => WatchPage(hashPath.split("/").pop()) };
  }
  if (hashPath.startsWith("/watch-party/")) {
    return { public: false, render: () => WatchPartyPage(hashPath.split("/").pop()) };
  }
  if (hashPath.startsWith("/content/")) {
    return { public: false, render: () => ContentDetailPage(hashPath.split("/").pop()) };
  }
  return routes.find((route) => route.path === hashPath) || routes[2];
}

async function hydrateSessionData() {
  if (!getCurrentUser()) return;
  try {
    await ensureFavoritesLoaded();
  } catch {
    // Keep route rendering responsive even when a background personalization fetch fails.
  }
}

function render() {
  if (!isAuthReady()) return;

  const route = resolveRoute();
  const isAuthed = Boolean(getCurrentUser());

  if (!route.public && !isAuthed) {
    location.hash = "/login";
    return;
  }

  if (route.public && isAuthed) {
    location.hash = "/";
    return;
  }

  document.querySelector("#app").innerHTML = route.public ? route.render() : AppLayout(route.render());
  document.dispatchEvent(new CustomEvent("page:mounted"));
}

function ensureHashRouteMounted() {
  const hashPath = location.hash.replace("#", "") || "/";
  const app = document.querySelector("#app");
  if (!app) return;

  if (hashPath.startsWith("/watch/") && !app.querySelector("#watchMount")) {
    render();
    return;
  }

  if (hashPath.startsWith("/watch-party/") && !app.querySelector("#watchPartyMount")) {
    render();
    return;
  }

  if (hashPath.startsWith("/content/") && !app.querySelector("#detailMount")) {
    render();
  }
}

export const router = {
  async start() {
    window.addEventListener("hashchange", render);
    document.addEventListener("auth:changed", () => {
      void hydrateSessionData().finally(() => {
        render();
      });
    });
    await initializeAuth();
    await hydrateSessionData();
    render();
    window.setTimeout(ensureHashRouteMounted, 0);
  },
  navigate(path) {
    location.hash = path;
  }
};
