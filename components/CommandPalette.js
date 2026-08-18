import { api } from "../services/api.js";

const destinations = [
  { label: "Home", path: "/", type: "Page" },
  { label: "Live TV", path: "/live-tv", type: "Page" },
  { label: "Discover", path: "/discover", type: "AI Search" },
  { label: "My Channel", path: "/my-channel", type: "AI Tool" },
  { label: "My List", path: "/my-list", type: "Library" },
  { label: "Profiles", path: "/profiles", type: "Account" },
  { label: "Stats", path: "/stats", type: "Analytics" },
  { label: "Social", path: "/social", type: "Social TV" },
  { label: "Admin", path: "/admin", type: "Management" }
];

export async function getCommandItems() {
  const catalogItems = await api.getAllCatalog().catch(() => []);
  return [
    ...destinations,
    ...catalogItems.map((item) => ({
      label: item.title,
      path: `/content/${item.id}`,
      type: `${item.category} • ${item.primaryGenre}`
    }))
  ];
}

export function CommandPalette() {
  return `
    <section class="command-palette" data-command-palette aria-label="Command palette">
      <div class="command-card">
        <div class="command-head">
          <span class="eyebrow">Quick jump</span>
          <kbd>Ctrl K</kbd>
        </div>
        <input data-command-input placeholder="Search content, pages, smart tools..." />
        <div class="command-results" data-command-results></div>
      </div>
    </section>
  `;
}
