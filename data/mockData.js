export const categories = ["All", "Movies", "Series", "Documentaries", "News", "Sports", "Technology", "Science", "Kids", "Entertainment"];

export const content = [
  {
    id: "ai-odyssey",
    title: "AI Odyssey",
    category: "Documentaries",
    year: 2026,
    duration: "52m",
    relevance: 97,
    channel: "TRT Belgesel",
    description: "A premium documentary about artificial intelligence, ethics, media personalization, and the future of semantic broadcasting.",
    color: "#143d43,#27666d,#e5a00d",
    backdrop: "#10131a,#19333b,#050609"
  },
  {
    id: "deep-space-signals",
    title: "Deep Space Signals",
    category: "Science",
    year: 2025,
    duration: "1h 08m",
    relevance: 91,
    channel: "BBC Earth",
    description: "Scientists use large-scale data models to interpret unknown signals from distant galaxies.",
    color: "#131c34,#244d83,#68a7ff",
    backdrop: "#08090d,#15213e,#091727"
  },
  {
    id: "robotics-frontier",
    title: "Robotics Frontier",
    category: "Technology",
    year: 2026,
    duration: "44m",
    relevance: 94,
    channel: "DW Documentary",
    description: "Factories, hospitals, and homes are reshaped by intelligent robotics and human-machine collaboration.",
    color: "#21172f,#6e3e77,#c77a11",
    backdrop: "#0a0d12,#30233e,#12070a"
  },
  {
    id: "istanbul-derby-live",
    title: "Istanbul Derby Live",
    category: "Sports",
    year: 2026,
    duration: "Live",
    relevance: 88,
    channel: "NTV Spor",
    description: "Live match coverage with second-screen statistics, social rooms, and synchronized co-watching.",
    color: "#27251d,#735f2c,#35d6a4",
    backdrop: "#151009,#3b2b12,#0a1110"
  },
  {
    id: "future-cities",
    title: "Future Cities",
    category: "Technology",
    year: 2025,
    duration: "49m",
    relevance: 86,
    channel: "CGTN",
    description: "Smart transportation, energy-aware neighborhoods, and connected public services across global cities.",
    color: "#10291f,#1e6f54,#68a7ff",
    backdrop: "#07100d,#143a31,#1f2531"
  },
  {
    id: "cinema-minds",
    title: "Cinema Minds",
    category: "Movies",
    year: 2024,
    duration: "1h 36m",
    relevance: 82,
    channel: "Synapse Movies",
    description: "A curated film about directors who built new cinematic languages in the streaming era.",
    color: "#29171c,#75414a,#e5a00d",
    backdrop: "#10090c,#2b1319,#2d2110"
  },
  {
    id: "northern-files",
    title: "Northern Files",
    category: "Series",
    year: 2026,
    duration: "8 episodes",
    relevance: 79,
    channel: "Nordic One",
    description: "A slow-burn investigative series powered by archive footage and tense newsroom decisions.",
    color: "#131b26,#2a425f,#b7c1d5",
    backdrop: "#07090d,#121f31,#28354b"
  },
  {
    id: "global-briefing",
    title: "Global Briefing",
    category: "News",
    year: 2026,
    duration: "Live",
    relevance: 76,
    channel: "BBC World",
    description: "International news with topic-based clipping and semantic event timelines.",
    color: "#271819,#7b1b25,#c77a11",
    backdrop: "#10090a,#301216,#08090d"
  },
  {
    id: "junior-lab",
    title: "Junior Lab",
    category: "Kids",
    year: 2026,
    duration: "24m",
    relevance: 72,
    channel: "Kids+",
    description: "A colorful science show that explains experiments with safe, visual activities.",
    color: "#173143,#35759c,#e5a00d",
    backdrop: "#0c1620,#18354b,#312710"
  },
  {
    id: "stage-night",
    title: "Stage Night",
    category: "Entertainment",
    year: 2025,
    duration: "1h 12m",
    relevance: 70,
    channel: "ShowTime",
    description: "Music, interviews, and live audience reactions from a late-night studio format.",
    color: "#26152c,#7e3f8d,#c77a11",
    backdrop: "#100714,#2b1431,#09090d"
  }
];

export const rows = {
  "Continue Watching": ["ai-odyssey", "istanbul-derby-live", "northern-files", "global-briefing"],
  "Recommended For You": ["ai-odyssey", "robotics-frontier", "deep-space-signals", "future-cities"],
  "Live Now": ["istanbul-derby-live", "global-briefing", "ai-odyssey", "stage-night"],
  Trending: ["robotics-frontier", "cinema-minds", "northern-files", "future-cities"],
  Movies: ["cinema-minds", "stage-night", "ai-odyssey", "deep-space-signals"],
  Series: ["northern-files", "junior-lab", "stage-night", "future-cities"],
  Documentaries: ["ai-odyssey", "deep-space-signals", "robotics-frontier", "future-cities"],
  "Technology & Science": ["robotics-frontier", "deep-space-signals", "future-cities", "junior-lab"],
  News: ["global-briefing", "future-cities", "ai-odyssey", "cinema-minds"],
  Sports: ["istanbul-derby-live", "global-briefing", "stage-night", "northern-files"]
};

export const channels = [
  { id: "trt-belgesel", logo: "TRT", name: "TRT Belgesel", category: "Documentary", current: "AI Odyssey", next: "Deep Ocean Data", live: true },
  { id: "bbc-earth", logo: "BBC", name: "BBC Earth", category: "Science", current: "Deep Space Signals", next: "Planet Code", live: true },
  { id: "ntv-spor", logo: "NTV", name: "NTV Spor", category: "Sports", current: "Istanbul Derby Live", next: "Post Match Room", live: true },
  { id: "dw", logo: "DW", name: "DW Documentary", category: "Technology", current: "Robotics Frontier", next: "Future Cities", live: true },
  { id: "bbc-world", logo: "WRD", name: "BBC World", category: "News", current: "Global Briefing", next: "Market Watch", live: true }
];

export const epgSlots = ["20:00", "21:00", "22:00", "23:00"];

export const epgPrograms = {
  "TRT Belgesel": ["Nature Codes", "AI Odyssey", "Archive Future", "Night Science"],
  "BBC Earth": ["Ocean Lab", "Deep Space Signals", "Planet Code", "Wild Cities"],
  "NTV Spor": ["Pre Match", "Istanbul Derby Live", "Tactical Board", "Fans Room"],
  "DW Documentary": ["Smart Mobility", "Robotics Frontier", "Future Cities", "World Report"],
  "BBC World": ["Global Briefing", "Europe Now", "The Context", "Business Live"]
};
