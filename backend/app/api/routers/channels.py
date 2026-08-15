from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.db import get_db
from app.repositories.channel_repository import ChannelRepository
from app.schemas.live_tv import ChannelLiveRead, ChannelRead
from app.services.live_tv.service import LiveTVService
from app.services.live_tv.sync_service import LiveTVSyncService

router = APIRouter(prefix="/channels", tags=["channels"])
channel_repository = ChannelRepository()
live_tv_service = LiveTVService()
sync_service = LiveTVSyncService()

WindowStart = Annotated[datetime | None, Query()]
WindowEnd = Annotated[datetime | None, Query()]


@router.get("", response_model=list[ChannelRead], status_code=status.HTTP_200_OK)
def list_channels(
    db: Session = Depends(get_db),
    start: WindowStart = None,
    end: WindowEnd = None,
) -> list[ChannelRead]:
    sync_service.ensure_ready(db=db, window_start=start, window_end=end)
    channels = channel_repository.list_active(db=db)
    return [live_tv_service.build_channel_read(channel) for channel in channels]


@router.get("/{channel_id}", response_model=ChannelRead, status_code=status.HTTP_200_OK)
def get_channel(
    channel_id: int,
    db: Session = Depends(get_db),
) -> ChannelRead:
    sync_service.ensure_ready(db=db)
    channel = channel_repository.get_by_id(db=db, channel_id=channel_id)
    if channel is None or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")
    return live_tv_service.build_channel_read(channel)


@router.get("/{channel_id}/live", response_model=ChannelLiveRead, status_code=status.HTTP_200_OK)
def get_channel_live(
    channel_id: int,
    db: Session = Depends(get_db),
) -> ChannelLiveRead:
    sync_service.ensure_ready(db=db)
    channel = channel_repository.get_by_id(db=db, channel_id=channel_id)
    if channel is None or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")
    return live_tv_service.build_channel_live_read(channel)
