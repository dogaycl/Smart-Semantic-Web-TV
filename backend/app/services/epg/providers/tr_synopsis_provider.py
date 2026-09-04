"""Programme text (and, where the feed has none, whole schedules) scraped from Turkish
broadcasters' own "yayın akışı" pages.

The free XMLTV feeds that populate the guide (epgshare01) publish only titles and times
for Turkish channels - no ``<desc>``. Several broadcasters publish a one/two sentence
synopsis per programme on their public schedule page, and a couple of channels that the
XMLTV feed does not list at all (TRT 2) publish a full timed schedule there. This provider
pulls both.

A synopsis describes the *programme* (e.g. "Seksenler"), not a single airing, so
``fetch_synopses`` is keyed by a normalised title and applies to every airing. Nothing
here invents text: an entry only gets a description that the broadcaster published for
that exact title.

Page shapes handled (first non-empty parser wins):
  * ``<script id="__NEXT_DATA__">`` JSON            - trt1, trtspor
  * inline ``"epg":[{"date":...,"data":[...]}]``     - trt2, trtbelgesel
  * ``<ul class="event-list">`` HTML                 - trtmuzik
  * ``tv.haberturk.com`` ``data-date``/``data-hours`` HTML
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.services.live_tv.providers.base import ExternalEPGEntry

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)
_INLINE_EPG_RE = re.compile(r'"epg"\s*:\s*(\[)')
_EVENT_LI_RE = re.compile(
    r'<li[^>]*\sdata-title="(?P<title>[^"]+)"[^>]*>(?P<body>.*?)</li>', re.S
)
_EVENT_TIME_RE = re.compile(r'datetime="(?P<date>\d{2}\.\d{2}\.\d{4})"[^>]*>\s*<span class="day">\s*(?:<a[^>]*>)?\s*(?P<time>\d{2}:\d{2})')
_EVENT_DESC_RE = re.compile(r'<p class="desc"[^>]*>\s*(?:<a[^>]*>)?\s*(?P<desc>[^<]*)')
_HABERTURK_RE = re.compile(
    r'data-date="(?P<date>\d{4}-\d{2}-\d{2})"\s+data-hours="(?P<time>\d{2}:\d{2})"[^>]*>'
    r'\s*<div>\s*<h3[^>]*>(?P<title>[^<]+)</h3>\s*<p[^>]*>(?P<desc>[^<]*)</p>'
)
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^0-9a-zçğıöşü ]+")
_TR_LOCAL = timezone(timedelta(hours=3))
_LOWER_MAP = str.maketrans({"İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"})


def normalize_title(value: str) -> str:
    lowered = (value or "").translate(_LOWER_MAP).lower()
    lowered = lowered.replace("’", " ").replace("'", " ").replace("`", " ").replace("-", " ")
    lowered = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", lowered).strip()


@dataclass(slots=True)
class ParsedProgramme:
    title: str
    synopsis: str
    start: datetime | None  # UTC


class TRSynopsisProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    # -- public API ---------------------------------------------------------

    def fetch_synopses(self, *, source_url: str) -> dict[str, str]:
        """``{normalized_title: synopsis}`` for a broadcaster schedule page."""
        synopses: dict[str, str] = {}
        for programme in self._fetch(source_url):
            key = normalize_title(programme.title)
            synopsis = programme.synopsis.strip()
            if not key or len(synopsis) < 12 or normalize_title(synopsis) == key:
                continue
            synopses.setdefault(key, synopsis)
        return synopses

    def fetch_entries(
        self,
        *,
        source_url: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[ExternalEPGEntry]:
        """Whole timed schedule, for channels the XMLTV feed does not list."""
        programmes = [p for p in self._fetch(source_url) if p.start is not None]
        programmes.sort(key=lambda p: p.start)  # type: ignore[arg-type,return-value]
        entries: list[ExternalEPGEntry] = []
        for index, programme in enumerate(programmes):
            start = programme.start
            assert start is not None
            if index + 1 < len(programmes):
                end = programmes[index + 1].start or (start + timedelta(hours=1))
            else:
                end = start + timedelta(hours=1)
            if end <= start:
                end = start + timedelta(minutes=30)
            if end <= window_start or start >= window_end:
                continue
            title = programme.title.strip()
            if not title:
                continue
            synopsis = programme.synopsis.strip()
            if normalize_title(synopsis) == normalize_title(title) or len(synopsis) < 12:
                synopsis = ""
            entries.append(
                ExternalEPGEntry(
                    external_id=f"broadcaster:{start.isoformat()}:{title}",
                    title=title,
                    description=synopsis or None,
                    category=None,
                    start_time=start,
                    end_time=end,
                    source="broadcaster",
                )
            )
        return entries

    # -- fetch + parse ----------------------------------------------------

    def _fetch(self, source_url: str) -> list[ParsedProgramme]:
        try:
            html = self._download(source_url)
        except httpx.HTTPError:
            return []
        for parser in (
            self._parse_next_data,
            self._parse_inline_epg,
            self._parse_event_list,
            self._parse_haberturk,
        ):
            programmes = parser(html)
            if programmes:
                return programmes
        return []

    def _download(self, source_url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }
        timeout = self.settings.live_tv_request_timeout_seconds * 3
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(source_url)
            response.raise_for_status()
            return response.text

    @staticmethod
    def _iso_utc(value: str | None) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @classmethod
    def _parse_next_data(cls, html: str) -> list[ParsedProgramme]:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
        out: list[ParsedProgramme] = []
        seen: set[tuple[str, str]] = set()

        def walk(node: object) -> None:
            if isinstance(node, dict):
                title = node.get("title")
                synopsis = node.get("synopsis")
                start = node.get("starttime")
                if isinstance(title, str) and isinstance(synopsis, str) and start:
                    key = (start, title)
                    if key not in seen:
                        seen.add(key)
                        out.append(ParsedProgramme(title, synopsis, cls._iso_utc(start)))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(data)
        return out

    @classmethod
    def _parse_inline_epg(cls, html: str) -> list[ParsedProgramme]:
        decoder = json.JSONDecoder()
        for anchor in _INLINE_EPG_RE.finditer(html):
            try:
                days, _ = decoder.raw_decode(html, anchor.start(1))
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(days, list):
                continue
            out: list[ParsedProgramme] = []
            for day in days:
                if not isinstance(day, dict):
                    continue
                for item in day.get("data") or []:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title")
                    synopsis = item.get("synopsis") or ""
                    if isinstance(title, str):
                        out.append(ParsedProgramme(title, synopsis, cls._iso_utc(item.get("starttime"))))
            if out:
                return out
        return []

    @classmethod
    def _parse_event_list(cls, html: str) -> list[ParsedProgramme]:
        if 'class="event-list"' not in html:
            return []
        out: list[ParsedProgramme] = []
        for li in _EVENT_LI_RE.finditer(html):
            body = li.group("body")
            desc_match = _EVENT_DESC_RE.search(body)
            time_match = _EVENT_TIME_RE.search(body)
            start = None
            if time_match:
                try:
                    naive = datetime.strptime(f"{time_match.group('date')} {time_match.group('time')}", "%d.%m.%Y %H:%M")
                    start = naive.replace(tzinfo=_TR_LOCAL).astimezone(timezone.utc)
                except ValueError:
                    start = None
            out.append(
                ParsedProgramme(
                    _html.unescape(li.group("title")).strip(),
                    _html.unescape(desc_match.group("desc")).strip() if desc_match else "",
                    start,
                )
            )
        return out

    @classmethod
    def _parse_haberturk(cls, html: str) -> list[ParsedProgramme]:
        out: list[ParsedProgramme] = []
        for row in _HABERTURK_RE.finditer(html):
            try:
                naive = datetime.strptime(f"{row.group('date')} {row.group('time')}", "%Y-%m-%d %H:%M")
                start = naive.replace(tzinfo=_TR_LOCAL).astimezone(timezone.utc)
            except ValueError:
                start = None
            out.append(
                ParsedProgramme(
                    _html.unescape(row.group("title")).strip(),
                    _html.unescape(row.group("desc")).strip(),
                    start,
                )
            )
        return out
