export function CategoryFilter(active = "All") {
  const libraryKey = active === "Movies" || active === "Series" ? active : "All";
  const selected = active === "Movies" || active === "Series" ? "All" : active;
  const groups = {
    Movies: ["All", "Action", "Comedy", "Drama", "Science Fiction", "Documentary"],
    Series: ["All", "Drama", "Comedy", "Science Fiction", "Documentary", "Action"],
    All: ["All", "Movies", "Series", "Documentaries", "Science Fiction", "Drama", "Comedy"]
  };
  const categories = groups[libraryKey] || groups.All;
  return `
    <div class="filter-bar">
      ${categories.map((category) => `<button class="chip ${category === selected ? "active" : ""}" data-category="${category}">${category}</button>`).join("")}
      <input class="input filter-search" data-title-search placeholder="Search by title" />
      <select class="select" data-sort>
        <option value="popularity_desc">Sort: Popularity</option>
        <option value="rating_desc">Sort: Rating</option>
        <option value="newest">Sort: Newest</option>
        <option value="title">Sort: Title</option>
      </select>
    </div>
  `;
}
