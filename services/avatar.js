// Shared profile-picture rendering. An avatar reference is stored on the user
// profile (`avatar_url`) as either a predefined token ("preset:<id>") or an
// http(s) image URL. Everything that shows a user - the profile page, the top
// navigation, Watch Together participants and chat messages - renders through
// here so a changed avatar is reflected consistently.

export const PRESET_AVATARS = [
  { id: "aurora", label: "Aurora", colors: ["#7f5bff", "#22d3ee"] },
  { id: "sunset", label: "Sunset", colors: ["#ff7e5f", "#feb47b"] },
  { id: "forest", label: "Forest", colors: ["#0ba360", "#3cba92"] },
  { id: "ocean", label: "Ocean", colors: ["#2193b0", "#6dd5ed"] },
  { id: "grape", label: "Grape", colors: ["#8e2de2", "#e94057"] },
  { id: "ember", label: "Ember", colors: ["#f83600", "#f9d423"] },
  { id: "slate", label: "Slate", colors: ["#485563", "#29323c"] },
  { id: "rose", label: "Rose", colors: ["#ee9ca7", "#ff5f8f"] },
  { id: "mint", label: "Mint", colors: ["#00b09b", "#96c93d"] },
  { id: "gold", label: "Gold", colors: ["#c79a3f", "#f6e27a"] },
  { id: "sky", label: "Sky", colors: ["#2980b9", "#6dd5fa"] },
  { id: "plum", label: "Plum", colors: ["#654ea3", "#eaafc8"] }
];

const PRESET_BY_ID = new Map(PRESET_AVATARS.map((preset) => [preset.id, preset]));
const DEFAULT_PRESET = PRESET_AVATARS[6]; // slate

export function avatarInitials(name) {
  return (
    String(name || "")
      .trim()
      .split(/\s+/)
      .map((part) => part[0])
      .filter(Boolean)
      .join("")
      .slice(0, 2)
      .toUpperCase() || "TV"
  );
}

function escapeAttr(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

// Accepts either the frontend-normalized shape ({ avatarUrl, displayName }) or a
// raw backend payload ({ avatar_url, display_name, username }).
function readUser(user = {}) {
  return {
    avatarRef: user.avatarUrl ?? user.avatar_url ?? null,
    name: user.displayName ?? user.display_name ?? user.username ?? user.name ?? ""
  };
}

export function resolveAvatar(user = {}) {
  const { avatarRef, name } = readUser(user);
  const initials = avatarInitials(name);

  if (typeof avatarRef === "string" && avatarRef.startsWith("preset:")) {
    const preset = PRESET_BY_ID.get(avatarRef.slice(7)) || DEFAULT_PRESET;
    return { kind: "preset", preset, initials };
  }
  if (typeof avatarRef === "string" && /^https?:\/\//i.test(avatarRef)) {
    return { kind: "image", src: avatarRef, initials };
  }
  return { kind: "preset", preset: DEFAULT_PRESET, initials };
}

// Returns an HTML string for a circular avatar. `size` is a pixel number.
export function avatarMarkup(user = {}, { size = 40, className = "" } = {}) {
  const resolved = resolveAvatar(user);
  const initials = escapeAttr(resolved.initials);
  const dimension = `${size}px`;
  const fontSize = `${Math.max(10, Math.round(size * 0.4))}px`;
  const classes = ["avatar-media", className].filter(Boolean).join(" ");
  const style = `width:${dimension};height:${dimension};font-size:${fontSize};`;

  if (resolved.kind === "image") {
    return `<span class="${classes}" style="${style}"><img src="${escapeAttr(resolved.src)}" alt="" loading="lazy" onerror="this.remove()" /><span class="avatar-media-fallback">${initials}</span></span>`;
  }

  const [from, to] = resolved.preset.colors;
  return `<span class="${classes}" style="${style}background:linear-gradient(135deg, ${from}, ${to});">${initials}</span>`;
}
