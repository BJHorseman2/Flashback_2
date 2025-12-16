"""Flashback API endpoints."""
from datetime import datetime, date
import random
from fastapi import APIRouter, Query, HTTPException
import structlog

from app.models.schemas import FlashbackResponse, GenerateRequest
from app.services.flashback import get_flashback_service

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/flashback", tags=["flashback"])


@router.get("", response_model=FlashbackResponse)
async def get_flashback(
    date: str = Query(
        ...,
        description="Date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
    lang: str = Query(
        default="en",
        description="Language code"
    )
) -> FlashbackResponse:
    """
    Get a flashback for a specific date.

    Returns cached result if available, or generates a new one.

    Response status:
    - ready: Scene is complete with all lens images
    - generating: Scene is being generated (poll again)
    - failed: Generation failed
    """
    logger.info("get_flashback", date=date, lang=lang)

    service = await get_flashback_service()
    return await service.get_flashback(date, lang)


@router.get("/today", response_model=FlashbackResponse)
async def get_today_flashback(
    lang: str = Query(default="en", description="Language code")
) -> FlashbackResponse:
    """Get flashback for today's date."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info("get_today_flashback", date=today, lang=lang)

    service = await get_flashback_service()
    return await service.get_flashback(today, lang)


@router.get("/random", response_model=FlashbackResponse)
async def get_random_flashback(
    lang: str = Query(default="en", description="Language code")
) -> FlashbackResponse:
    """Get flashback for a random date in history."""
    # Generate random date (any date in past 200 years)
    year = random.randint(1825, datetime.utcnow().year)
    month = random.randint(1, 12)

    # Handle varying days per month
    if month in [4, 6, 9, 11]:
        day = random.randint(1, 30)
    elif month == 2:
        day = random.randint(1, 28)
    else:
        day = random.randint(1, 31)

    random_date = f"{year}-{month:02d}-{day:02d}"
    logger.info("get_random_flashback", date=random_date, lang=lang)

    service = await get_flashback_service()
    return await service.get_flashback(random_date, lang)


@router.post("/generate", response_model=FlashbackResponse)
async def generate_flashback(request: GenerateRequest) -> FlashbackResponse:
    """
    Explicitly request generation of a new flashback.

    Use force_regenerate=true to regenerate even if cached.
    """
    logger.info(
        "generate_flashback",
        date=request.date,
        lang=request.lang,
        force=request.force_regenerate
    )

    service = await get_flashback_service()
    return await service.get_flashback(request.date, request.lang)
