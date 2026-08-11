import { getCurrentUser, initializeAuth, isAuthReady } from "./contexts/authContext.js";
import { AppLayout } from "./components/AppLayout.js";
import { LoginPage } from "./pages/LoginPage.js";
import { RegisterPage } from "./pages/RegisterPage.js";
import { HomePage } from "./pages/HomePage.js";
import { LiveTvPage } from "./pages/LiveTvPage.js";
import { LibraryPage } from "./pages/LibraryPage.js";
import { OnDemandPage } from "./pages/OnDemandPage.js";
import { DiscoverPage } from "./pages/DiscoverPage.js";
import { ContentDetailPage } from "./pages/ContentDetailPage.js";
import { MyListPage } from "./pages/MyListPage.js";
import { ProfilePage } from "./pages/ProfilePage.js";
import { ProfilesPage } from "./pages/ProfilesPage.js";
import { StatsPage } from "./pages/StatsPage.js";
import { AdminPage } from "./pages/AdminPage.js";
import { SocialPage } from "./pages/SocialPage.js";
import { HistoryPage } from "./pages/HistoryPage.js";
import { AIHubPage } from "./pages/AIHubPage.js";
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
  { path: "/ai", render: AIHubPage },
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
  if (hashPath.startsWith("/content/")) {
    return { public: false, render: () => ContentDetailPage(hashPath.split("/").pop()) };
  }
  return routes.find((route) => route.path === hashPath) || routes[2];
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

export const router = {
  async start() {
    window.addEventListener("hashchange", render);
    document.addEventListener("auth:changed", render);
    await initializeAuth();
    render();
  },
  navigate(path) {
    location.hash = path;
  }
};
