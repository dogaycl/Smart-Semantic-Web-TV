import { channels, content, epgPrograms, epgSlots, rows } from "../data/mockData.js";

const delay = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 80));

export const api = {
  getFeatured() {
    return delay(content[0]);
  },
  getRows() {
    const mapped = Object.fromEntries(
      Object.entries(rows).map(([title, ids]) => [title, ids.map((id) => content.find((item) => item.id === id))])
    );
    return delay(mapped);
  },
  getContentById(id) {
    return delay(content.find((item) => item.id === id));
  },
  getContentByCategory(category) {
    return delay(category === "All" ? content : content.filter((item) => item.category === category));
  },
  searchSemantic(query) {
    const lowered = query.toLowerCase();
    const results = content
      .filter((item) => `${item.title} ${item.category} ${item.description}`.toLowerCase().includes("ai") || lowered.includes(item.category.toLowerCase()) || item.relevance > 84)
      .sort((a, b) => b.relevance - a.relevance);
    return delay(results);
  },
  getLiveTv() {
    return delay({ channels, epgSlots, epgPrograms });
  }
};
