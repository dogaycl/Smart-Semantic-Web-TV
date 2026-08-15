from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.db import get_db
from app.repositories.channel_repository import ChannelRepository
from app.schemas.live_tv import EPGWindowResponse
from app.services.epg.service import EPGService
from app.services.live_tv.sync_service import LiveTVSyncService

router = APIRouter(prefix="/epg", tags=["epg"])
channel_repository = ChannelRepository()
epg_service = EPGService()
sync_service = LiveTVSyncService()

WindowStart = Annotated[datetime | None, Query()]
WindowEnd = Annotated[datetime | None, Query()]
SlotMinutes = Annotated[int, Query(ge=15, le=180)]


@router.get("", response_model=EPGWindowResponse, status_code=status.HTTP_200_OK)
def get_epg_window(
    db: Session = Depends(get_db),
    start: WindowStart = None,
    end: WindowEnd = None,
    slot_minutes: SlotMinutes = 60,
) -> EPGWindowResponse:
    if start is None or end is None:
        start, end = epg_service.default_window(hours=4)
    sync_service.ensure_ready(db=db, window_start=start, window_end=end)
    channels = channel_repository.list_active(db=db)
    return epg_service.get_window(db=db, channels=channels, start=start, end=end, slot_minutes=slot_minutes)


@router.get("/{channel_id}", response_model=EPGWindowResponse, status_code=status.HTTP_200_OK)
def get_channel_epg_window(
    channel_id: int,
    db: Session = Depends(get_db),
    start: WindowStart = None,
    end: WindowEnd = None,
    slot_minutes: SlotMinutes = 60,
) -> EPGWindowResponse:
    if start is None or end is None:
        start, end = epg_service.default_window(hours=4)
    sync_service.ensure_ready(db=db, window_start=start, window_end=end)
    channel = channel_repository.get_by_id(db=db, channel_id=channel_id)
    if channel is None or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")
    return epg_service.get_window(db=db, channels=[channel], start=start, end=end, slot_minutes=slot_minutes)
