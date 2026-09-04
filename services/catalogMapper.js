function byPopularityDesc(a, b) {
  return (b.popularityValue || 0) - (a.popularityValue || 0) || (b.ratingValue || 0) - (a.ratingValue || 0);
}

function byRatingDesc(a, b) {
  return (b.ratingValue || 0) - (a.ratingValue || 0) || (b.popularityValue || 0) - (a.popularityValue || 0);
}

function byReleaseDesc(a, b) {
  return String(b.releaseDate || "").localeCompare(String(a.releaseDate || "")) || byPopularityDesc(a, b);
}

function normalizeVideo(video) {
  if (!video) return null;
  return {
    name: video.name,
    site: video.site,
    type: video.type,
    official: video.official,
    publishedAt: video.published_at,
    embedUrl: video.embed_url
  };
}

export function normalizeCatalogSummary(item) {
  const genres = item.genres || [];
  return {
    id: item.slug,
    slug: item.slug,
    backendId: item.id,
    tmdbId: item.tmdb_id,
    contentType: item.content_type,
    title: item.title,
    originalTitle: item.original_title,
    category: item.category_label,
    primaryGenre: item.primary_genre || item.category_label,
    genres,
    year: item.year,
    releaseDate: item.release_date,
    duration: item.runtime_display,
    runtimeMinutes: item.runtime_minutes,
    imdb: item.rating != null ? item.rating.toFixed(1) : null,
    ratingValue: item.rating,
    popularityValue: item.popularity,
    description: item.overview || "No description is available yet.",
    poster: item.poster_url,
    backdrop: item.backdrop_url,
    status: item.status,
    language: item.language ? String(item.language).toUpperCase() : null,
    numberOfSeasons: item.number_of_seasons,
    numberOfEpisodes: item.number_of_episodes,
    tmdbUrl: item.tmdb_url,
    hasTrailer: item.has_trailer,
    isPlayable: Boolean(item.is_playable),
    lastSyncedAt: item.last_synced_at
  };
}

export function normalizeCatalogDetail(item) {
  const summary = normalizeCatalogSummary(item);
  return {
    ...summary,
    topCast: item.top_cast || [],
    topCrew: item.top_crew || [],
    videos: (item.videos || []).map(normalizeVideo),
    trailer: normalizeVideo(item.trailer),
    seasons: (item.seasons || []).map((season) => ({
      seasonNumber: season.season_number,
      name: season.name,
      overview: season.overview,
      airDate: season.air_date,
      episodeCount: season.episode_count,
      poster: season.poster_url
    })),
    relatedItems: (item.related_items || []).map(normalizeCatalogSummary),
    attribution: item.attribution || null
  };
}

export function pickFeaturedCatalogItem(items) {
  return [...items]
    .filter((item) => item.backdrop || item.poster)
    .sort(byPopularityDesc)[0] || items[0] || null;
}

export function buildCatalogRows(items) {
  const movies = items.filter((item) => item.contentType === "movie").sort(byPopularityDesc);
  const series = items.filter((item) => item.contentType === "tv").sort(byPopularityDesc);
  const docsAndScience = items
    .filter((item) => item.genres.includes("Documentary") || item.genres.includes("Science Fiction") || item.genres.includes("Sci-Fi & Fantasy"))
    .sort(byPopularityDesc);
  const criticallyRated = [...items].sort(byRatingDesc);
  const recentlyAdded = [...items].sort(byReleaseDesc);

  return {
    "Popular Movies": movies.slice(0, 10),
    "Top Series": series.slice(0, 10),
    "Documentaries & Science": docsAndScience.slice(0, 10),
    "Critically Rated": criticallyRated.slice(0, 10),
    "Recently Added": recentlyAdded.slice(0, 10)
  };
}

export function filterCatalogForAi(items, preferences) {
  return items
    .filter((item) => !preferences.useMinImdb || Number(item.imdb || 0) >= preferences.minImdb)
    .filter((item) => !preferences.useReleaseAfter || (item.year || 0) >= preferences.releaseAfter)
    .filter((item) => {
      if (!preferences.contentTypes?.length) return true;
      return preferences.contentTypes.some((type) => {
        if (type === "Movies") return item.contentType === "movie";
        if (type === "Series") return item.contentType === "tv";
        if (type === "Documentaries") return item.genres.includes("Documentary");
        if (type === "Science" || type === "Technology") return item.genres.includes("Science Fiction") || item.genres.includes("Sci-Fi & Fantasy");
        if (type === "Comedy") return item.genres.includes("Comedy");
        if (type === "Drama") return item.genres.includes("Drama");
        return false;
      });
    })
    .sort(byRatingDesc);
}
