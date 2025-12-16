"""Database models for Flashback Daily."""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Text,
    Float,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from app.config import get_settings

Base = declarative_base()


class SceneStatus(str, Enum):
    """Status of a flashback scene."""
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class AssetStatus(str, Enum):
    """Status of an individual lens asset."""
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class FlashbackScene(Base):
    """A historical event scene with 5 lens recreations."""
    __tablename__ = "flashback_scene"

    scene_id = Column(String(255), primary_key=True)  # YYYY-MM-DD__lang__eventSlug__v{n}
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    lang = Column(String(10), nullable=False, default="en")
    event_title = Column(String(500), nullable=False)
    event_year = Column(Integer, nullable=True)
    event_summary = Column(Text, nullable=False)
    event_summary_source_text = Column(Text, nullable=False)
    wikipedia_url = Column(String(1000), nullable=False)
    wikidata_qid = Column(String(20), nullable=True)
    rank_signals = Column(JSON, nullable=True)
    scene_spec = Column(JSON, nullable=True)
    status = Column(SQLEnum(SceneStatus), default=SceneStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    assets = relationship("FlashbackAsset", back_populates="scene", cascade="all, delete-orphan")


class FlashbackAsset(Base):
    """A single lens image for a scene."""
    __tablename__ = "flashback_asset"

    asset_id = Column(String(255), primary_key=True)
    scene_id = Column(String(255), ForeignKey("flashback_scene.scene_id"), nullable=False)
    lens_id = Column(Integer, nullable=False)  # 1-5
    lens_name = Column(String(50), nullable=False)
    image_url = Column(String(1000), nullable=True)
    prompt_used = Column(Text, nullable=True)
    qc_result = Column(JSON, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    status = Column(SQLEnum(AssetStatus), default=AssetStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scene = relationship("FlashbackScene", back_populates="assets")


class UserUsage(Base):
    """Track user usage for rate limiting."""
    __tablename__ = "user_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    week_start = Column(String(10), nullable=False)  # YYYY-MM-DD (Monday)
    usage_count = Column(Integer, default=0, nullable=False)
    is_pro = Column(Integer, default=0, nullable=False)  # 0 = free, 1 = pro
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Database engine and session factory
def get_engine():
    """Create async database engine."""
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


def get_session_factory():
    """Create async session factory."""
    engine = get_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
