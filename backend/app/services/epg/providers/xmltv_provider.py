from datetime import datetime, timedelta, timezone
import gzip
import io
import re
import xml.etree.ElementTree as ET

import httpx

from app.core.config import get_settings
from app.services.live_tv.providers.base import ExternalEPGEntry

XMLTV_DATE_RE = re.compile(r"^(?P<stamp>\d{8,14})(?:\s?(?P<offset>[+-]\d{4}|Z))?$")


class XMLTVProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_entries(
        self,
        *,
        source_url: str,
        channel_ids: set[str],
        window_start: datetime,
        window_end: datetime,
    ) -> dict[str, list[ExternalEPGEntry]]:
        if not channel_ids:
            return {}

        payload = self._download(source_url)
        stream: io.BytesIO | gzip.GzipFile
        if source_url.endswith(".gz"):
            stream = gzip.GzipFile(fileobj=io.BytesIO(payload))
        else:
            stream = io.BytesIO(payload)

        matches: dict[str, list[ExternalEPGEntry]] = {channel_id: [] for channel_id in channel_ids}
        context = ET.iterparse(stream, events=("end",))
        for _, elem in context:
            if elem.tag != "programme":
                continue

            channel_id = elem.attrib.get("channel")
            if channel_id not in channel_ids:
                elem.clear()
                continue

            start_time = self.parse_datetime(elem.attrib.get("start"))
            end_time = self.parse_datetime(elem.attrib.get("stop")) or start_time
            if start_time is None or end_time <= window_start or start_time >= window_end:
                elem.clear()
                continue

            title = (elem.findtext("title") or "").strip()
            if not title:
                elem.clear()
                continue

            category = (elem.findtext("category") or "").strip() or None
            description = (elem.findtext("desc") or "").strip() or None
            external_id = f"{channel_id}:{start_time.isoformat()}:{title}"
            matches[channel_id].append(
                ExternalEPGEntry(
                    external_id=external_id,
                    title=title,
                    description=description,
                    category=category,
                    start_time=start_time,
                    end_time=end_time,
                    source="xmltv",
                )
            )
            elem.clear()

        return matches

    def _download(self, source_url: str) -> bytes:
        with httpx.Client(timeout=self.settings.live_tv_request_timeout_seconds * 5, follow_redirects=True) as client:
            response = client.get(source_url)
            response.raise_for_status()
            return response.content

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None

        match = XMLTV_DATE_RE.match(value.strip())
        if not match:
            return None

        stamp = match.group("stamp")
        offset = match.group("offset")
        fmt = {
            8: "%Y%m%d",
            10: "%Y%m%d%H",
            12: "%Y%m%d%H%M",
            14: "%Y%m%d%H%M%S",
        }.get(len(stamp))
        if fmt is None:
            return None

        parsed = datetime.strptime(stamp, fmt)
        if offset in (None, "Z"):
            return parsed.replace(tzinfo=timezone.utc)

        sign = 1 if offset.startswith("+") else -1
        hours = int(offset[1:3])
        minutes = int(offset[3:5])
        tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
        return parsed.replace(tzinfo=tz).astimezone(timezone.utc)
