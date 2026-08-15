import { getCurrentUser, logout } from "../contexts/authContext.js";
import { Sidebar } from "./Sidebar.js";
import { Topbar } from "./Topbar.js";
import { AIAssistant } from "./AIAssistant.js";
import { CommandPalette, getCommandItems } from "./CommandPalette.js";

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
    const menuButton = document.querySelector("[data-menu-toggle]");
    const accountMenu = document.querySelector("[data-account-menu]");
    menuButton?.addEventListener("click", (event) => {
      event.stopPropagation();
      accountMenu?.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", accountMenu?.classList.contains("open") ? "true" : "false");
    });
    accountMenu?.addEventListener("click", (event) => {
      event.stopPropagation();
    });
    document.addEventListener("click", () => {
      accountMenu?.classList.remove("open");
      menuButton?.setAttribute("aria-expanded", "false");
    });
    const aiPanel = document.querySelector("[data-ai-panel]");
    const aiToggle = document.querySelector("[data-ai-toggle]");
    const openAi = () => {
      aiPanel?.classList.add("open");
      aiToggle?.setAttribute("aria-expanded", "true");
      document.querySelector("[data-ai-input]")?.focus();
    };
    const closeAi = () => {
      aiPanel?.classList.remove("open");
      aiToggle?.setAttribute("aria-expanded", "false");
    };
    aiToggle?.addEventListener("click", openAi);
    document.querySelector("[data-ai-close]")?.addEventListener("click", closeAi);
    document.querySelectorAll("[data-ai-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelector("[data-ai-input]").value = button.dataset.aiPrompt;
        openAi();
      });
    });
    document.querySelector("[data-ai-form]")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = document.querySelector("[data-ai-input]");
      const chat = document.querySelector(".ai-chat");
      const value = input.value.trim();
      if (!value) return;
      chat.insertAdjacentHTML("beforeend", `<div class="ai-message user">${value}</div>`);
      chat.insertAdjacentHTML("beforeend", `<div class="ai-message">I found semantic matches in Movies, Series, and Technology. Try opening Discover for full results.</div>`);
      sessionStorage.setItem("synapse.semantic.query", value);
      input.value = "";
      chat.scrollTop = chat.scrollHeight;
    });
    const palette = document.querySelector("[data-command-palette]");
    const commandInput = document.querySelector("[data-command-input]");
    const commandResults = document.querySelector("[data-command-results]");
    const renderCommands = async (query = "") => {
      const normalized = query.toLowerCase();
      const commandItems = await getCommandItems();
      const matches = commandItems
        .filter((item) => `${item.label} ${item.type}`.toLowerCase().includes(normalized))
        .slice(0, 8);
      commandResults.innerHTML = matches.map((item) => `
        <button data-command-path="${item.path}">
          <strong>${item.label}</strong>
          <span>${item.type}</span>
        </button>
      `).join("");
      commandResults.querySelectorAll("[data-command-path]").forEach((button) => {
        button.addEventListener("click", () => {
          palette.classList.remove("open");
          location.hash = button.dataset.commandPath;
        });
      });
    };
    const openPalette = () => {
      renderCommands();
      palette?.classList.add("open");
      commandInput?.focus();
    };
    const closePalette = () => palette?.classList.remove("open");
    document.querySelector("[data-command-open]")?.addEventListener("click", openPalette);
    commandInput?.addEventListener("input", () => renderCommands(commandInput.value));
    palette?.addEventListener("click", (event) => {
      if (event.target === palette) closePalette();
    });
    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openPalette();
      }
      if (event.key === "Escape") closePalette();
    });
  });

  return `
    <div class="app-layout vynex-layout">
      ${Sidebar(user)}
      <div class="main">
        ${Topbar(user)}
        ${content}
      </div>
      ${AIAssistant()}
      ${CommandPalette()}
    </div>
  `;
}
