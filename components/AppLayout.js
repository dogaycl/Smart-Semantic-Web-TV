import { getCurrentUser, logout } from "../contexts/authContext.js";
import { Sidebar } from "./Sidebar.js";
import { Topbar } from "./Topbar.js";

export function AppLayout(content) {
  const user = getCurrentUser();
  queueMicrotask(() => {
    document.querySelectorAll("[data-logout]").forEach((element) => {
      element.addEventListener("click", () => {
        logout();
        location.hash = "/login";
      });
    });
    document.querySelector("[data-sidebar-toggle]")?.addEventListener("click", () => {
      document.querySelector(".sidebar")?.classList.toggle("collapsed");
    });
    document.querySelector("[data-global-search]")?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      sessionStorage.setItem("synapse.semantic.query", event.currentTarget.value);
      location.hash = "/discover";
    });
  });

  return `
    <div class="app-layout vynex-layout">
      ${Sidebar(user)}
      <div class="main">
        ${Topbar(user)}
        ${content}
      </div>
    </div>
  `;
}
