"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    """A source reference for the event."""
    label: str
    url: str


class Lens(BaseModel):
    """A single lens image in the flashback."""
    lens_id: int = Field(ge=1, le=5)
    name: str
    image_url: Optional[str] = None


class LocationSpec(BaseModel):
    """Location specification."""
    name: str
    coords: list[float] = Field(default_factory=lambda: [0.0, 0.0])


class SettingSpec(BaseModel):
    """Setting specification."""
    environment: str = "outdoor"  # indoor|outdoor|mixed
    time_of_day: str = "day"  # day|night|unknown


class SceneSpec(BaseModel):
    """The truth contract for image generation."""
    style_pack: str = "editorial_realism_v1"
    event_title: str
    year: int
    location: LocationSpec
    setting: SettingSpec
    era_cues: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    key_objects: list[str] = Field(default_factory=list)
    mood: str = "uncertain"
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=lambda: [
        "readable text", "logos", "watermarks",
        "modern smartphones", "modern cars",
        "blood/gore", "identifiable celebrity likeness"
    ])


class SceneResponse(BaseModel):
    """Response for a single flashback scene."""
    scene_id: str
    date: str
    title: str
    year: Optional[int] = None
    summary: str
    sources: list[Source]
    lenses: list[Lens]
    disclosure: str = "AI Recreation"


class FlashbackResponse(BaseModel):
    """Full flashback API response."""
    status: str  # ready | generating | failed
    scene: Optional[SceneResponse] = None
    message: Optional[str] = None
    retry_after: Optional[int] = None  # seconds to wait before polling again


class RankSignals(BaseModel):
    """Signals used to rank event importance."""
    pageviews_30d: Optional[int] = None
    pageviews_365d: Optional[int] = None
    sitelinks_count: Optional[int] = None
    lede_length: Optional[int] = None
    final_score: float = 0.0


class OnThisDayEvent(BaseModel):
    """An event from the OnThisDay API."""
    text: str
    year: int
    pages: list[dict] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    """Request to generate a new flashback."""
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    lang: str = "en"
    force_regenerate: bool = False
