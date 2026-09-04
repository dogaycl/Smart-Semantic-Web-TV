import { getCurrentUser, logout } from "../contexts/authContext.js";
import { api } from "../services/api.js?v=55";
import { Sidebar } from "./Sidebar.js?v=55";
import { Topbar } from "./Topbar.js?v=55";
import { AIAssistant } from "./AIAssistant.js";
import { CommandPalette, getCommandItems } from "./CommandPalette.js?v=55";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getAssistantContext() {
  const element = document.querySelector("[data-assistant-context]");
  if (!element?.dataset?.contextType) return null;

  return {
    context_type: element.dataset.contextType,
    content_slug: element.dataset.contentSlug || undefined,
    channel_id: element.dataset.channelId ? Number(element.dataset.channelId) : undefined,
    epg_entry_id: element.dataset.epgEntryId ? Number(element.dataset.epgEntryId) : undefined,
    label: element.dataset.contextLabel || "Current content"
  };
}

function updateAssistantContextLabel() {
  const label = getAssistantContext()?.label || "Open a movie, series, or live channel";
  document.querySelector("[data-ai-context-label]")?.replaceChildren(document.createTextNode(label));
}

function appendAiMessage(chat, html, className = "") {
  const classes = ["ai-message", className].filter(Boolean).join(" ");
  chat.insertAdjacentHTML("beforeend", `<div class="${classes}">${html}</div>`);
  chat.scrollTop = chat.scrollHeight;
}

function renderAssistantReply(payload) {
  const sources = (payload.sources || []).slice(0, 3).map((source) => `
    <li><strong>${escapeHtml(source.title)}</strong>: ${escapeHtml(source.snippet)}</li>
  `).join("");
  const followUps = (payload.follow_up_questions || []).map((question) => `
    <button data-ai-prompt="${escapeHtml(question)}">${escapeHtml(question)}</button>
  `).join("");

  return `
    <div class="assistant-answer-copy">${escapeHtml(payload.answer)}</div>
    ${payload.limitation_note ? `<p class="muted">${escapeHtml(payload.limitation_note)}</p>` : ""}
    ${sources ? `<ul class="ai-source-list">${sources}</ul>` : ""}
    ${followUps ? `<div class="ai-suggestions">${followUps}</div>` : ""}
  `;
}

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
      updateAssistantContextLabel();
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
    document.addEventListener("click", (event) => {
      const promptButton = event.target.closest("[data-ai-prompt]");
      if (!promptButton) return;
      document.querySelector("[data-ai-input]").value = promptButton.dataset.aiPrompt;
      openAi();
    });
    document.querySelector("[data-ai-form]")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = document.querySelector("[data-ai-input]");
      const chat = document.querySelector(".ai-chat");
      const value = input.value.trim();
      if (!value) return;
      const context = getAssistantContext();
      appendAiMessage(chat, escapeHtml(value), "user");
      input.value = "";
      if (!context) {
        appendAiMessage(
          chat,
          "Open a movie, series, or live channel first so I can answer with trusted content context."
        );
        return;
      }

      appendAiMessage(chat, "Checking trusted context...", "loading");
      const loadingNode = chat.lastElementChild;

      try {
        const response = await api.assistantChat({
          message: value,
          context_type: context.context_type,
          content_slug: context.content_slug,
          channel_id: context.channel_id,
          epg_entry_id: context.epg_entry_id
        });
        loadingNode?.remove();
        appendAiMessage(chat, renderAssistantReply(response));
      } catch (error) {
        loadingNode?.remove();
        if (error?.status === 401) {
          logout();
          location.hash = "/login";
          return;
        }
        appendAiMessage(chat, escapeHtml(error.message || "AI assistant is unavailable right now."));
      }
    });
    document.addEventListener("assistant:context-changed", updateAssistantContextLabel);
    updateAssistantContextLabel();
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
