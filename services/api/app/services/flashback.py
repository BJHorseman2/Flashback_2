"""Flashback orchestration service - coordinates the full generation flow."""
import re
from datetime import datetime
from typing import Optional
import structlog

from app.models.database import (
    FlashbackScene, FlashbackAsset, SceneStatus, AssetStatus,
    get_session_factory
)
from app.models.schemas import (
    SceneSpec, FlashbackResponse, SceneResponse, Source, Lens
)
from app.services.wikimedia import WikimediaService, get_wikimedia_service
from app.services.ranking import EventRankingService
from app.services.scene_spec import SceneSpecGenerator
from app.services.summary import SummaryGenerator
from app.services.image_gen import ImageGenerationService, get_image_service, LENS_SPECS
from app.services.qc import QualityControlService, get_qc_service

logger = structlog.get_logger()

MAX_QC_RETRIES = 2


class FlashbackService:
    """
    Main orchestration service for generating flashbacks.

    Flow:
    1. Check cache for existing scene
    2. Fetch OnThisDay events
    3. Rank and select top event
    4. Generate SceneSpec
    5. Generate summary
    6. Generate 5 lens images with QC
    7. Store and return
    """

    def __init__(
        self,
        wikimedia: WikimediaService,
        image_service: ImageGenerationService,
        qc_service: QualityControlService
    ):
        self.wikimedia = wikimedia
        self.image_service = image_service
        self.qc_service = qc_service
        self.ranking_service = EventRankingService(wikimedia)
        self.scene_spec_generator = SceneSpecGenerator(wikimedia)
        self.summary_generator = SummaryGenerator()
        self.session_factory = get_session_factory()

    async def get_flashback(self, date: str, lang: str = "en") -> FlashbackResponse:
        """
        Get or generate a flashback for the given date.

        Args:
            date: Date in YYYY-MM-DD format
            lang: Language code (default: en)

        Returns:
            FlashbackResponse with status and scene data
        """
        # Parse date
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            month = dt.month
            day = dt.day
        except ValueError:
            return FlashbackResponse(
                status="failed",
                message="Invalid date format. Use YYYY-MM-DD."
            )

        # Check for existing scene
        scene_id_prefix = f"{date}__{lang}__"
        existing = await self._find_existing_scene(scene_id_prefix)

        if existing and existing.status == SceneStatus.READY:
            return self._build_response(existing)

        if existing and existing.status == SceneStatus.GENERATING:
            return FlashbackResponse(
                status="generating",
                message="Scene is being generated",
                retry_after=10
            )

        # Generate new scene
        return await self._generate_scene(date, month, day, lang)

    async def _find_existing_scene(self, scene_id_prefix: str) -> Optional[FlashbackScene]:
        """Find an existing scene by ID prefix."""
        async with self.session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(FlashbackScene)
                .where(FlashbackScene.scene_id.startswith(scene_id_prefix))
                .order_by(FlashbackScene.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _generate_scene(
        self,
        date: str,
        month: int,
        day: int,
        lang: str
    ) -> FlashbackResponse:
        """Generate a new flashback scene."""
        logger.info("generating_scene", date=date, lang=lang)

        # 1. Fetch OnThisDay events
        events = await self.wikimedia.get_on_this_day_events(month, day, lang)

        if not events:
            return FlashbackResponse(
                status="failed",
                message="No events found for this date"
            )

        # 2. Rank and select top event
        top_event = await self.ranking_service.select_top_event(events, lang)

        if not top_event:
            return FlashbackResponse(
                status="failed",
                message="Could not rank events for this date"
            )

        # 3. Get additional data
        primary_page = top_event.get("primary_page", {})
        title = primary_page.get("title", "")
        year = top_event.get("year", 0)

        wikidata = await self.wikimedia.get_wikidata_info(title, lang)
        extract = await self.wikimedia.get_article_extract(title, lang)

        # 4. Generate SceneSpec
        scene_spec = await self.scene_spec_generator.generate(
            top_event, wikidata, extract
        )

        # 5. Generate summary
        event_text = top_event.get("text", "")
        summary = self.summary_generator.generate(event_text, extract or "", year)

        # 6. Create scene record
        slug = self._slugify(title)
        scene_id = f"{date}__{lang}__{slug}__v1"

        wikipedia_url = primary_page.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not wikipedia_url:
            wikipedia_url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"

        scene = FlashbackScene(
            scene_id=scene_id,
            date=date,
            lang=lang,
            event_title=title,
            event_year=year,
            event_summary=summary,
            event_summary_source_text=event_text,
            wikipedia_url=wikipedia_url,
            wikidata_qid=wikidata.get("qid") if wikidata else None,
            rank_signals=top_event.get("rank_signals", {}).model_dump() if hasattr(top_event.get("rank_signals"), "model_dump") else top_event.get("rank_signals"),
            scene_spec=scene_spec.model_dump(),
            status=SceneStatus.GENERATING
        )

        # Create asset placeholders
        assets = []
        for lens_id in range(1, 6):
            asset = FlashbackAsset(
                asset_id=f"{scene_id}__lens_{lens_id}",
                scene_id=scene_id,
                lens_id=lens_id,
                lens_name=LENS_SPECS[lens_id]["name"],
                status=AssetStatus.PENDING
            )
            assets.append(asset)

        # Save to database
        async with self.session_factory() as session:
            session.add(scene)
            for asset in assets:
                session.add(asset)
            await session.commit()

        # 7. Generate images (this would normally be queued)
        await self._generate_all_lenses(scene, scene_spec, assets)

        # Reload scene
        async with self.session_factory() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            result = await session.execute(
                select(FlashbackScene)
                .options(selectinload(FlashbackScene.assets))
                .where(FlashbackScene.scene_id == scene_id)
            )
            scene = result.scalar_one()

        return self._build_response(scene)

    async def _generate_all_lenses(
        self,
        scene: FlashbackScene,
        scene_spec: SceneSpec,
        assets: list[FlashbackAsset]
    ):
        """Generate all 5 lens images with QC."""
        async with self.session_factory() as session:
            all_success = True

            for asset in assets:
                success = await self._generate_lens_with_qc(
                    session, scene, scene_spec, asset
                )
                if not success:
                    all_success = False

            # Update scene status
            scene.status = SceneStatus.READY if all_success else SceneStatus.FAILED
            session.add(scene)
            await session.commit()

    async def _generate_lens_with_qc(
        self,
        session,
        scene: FlashbackScene,
        scene_spec: SceneSpec,
        asset: FlashbackAsset
    ) -> bool:
        """Generate a single lens image with QC retries."""
        asset.status = AssetStatus.GENERATING
        session.add(asset)
        await session.commit()

        prompt = self.image_service.build_prompt(scene_spec, asset.lens_id)
        asset.prompt_used = prompt

        for attempt in range(MAX_QC_RETRIES + 1):
            asset.attempts = attempt + 1

            # Generate image
            image_bytes = await self.image_service.generate_image(prompt)

            if not image_bytes:
                logger.warning(
                    "image_generation_failed",
                    scene_id=scene.scene_id,
                    lens_id=asset.lens_id,
                    attempt=attempt
                )
                continue

            # Run QC check
            qc_result = await self.qc_service.check_image(
                image_bytes, scene_spec, asset.lens_id
            )
            asset.qc_result = qc_result.to_dict()

            if qc_result.passed:
                # Upload image
                url = await self.image_service.upload_image(
                    image_bytes, scene.scene_id, asset.lens_id
                )

                if url:
                    asset.image_url = url
                    asset.status = AssetStatus.READY
                    session.add(asset)
                    await session.commit()

                    logger.info(
                        "lens_generated",
                        scene_id=scene.scene_id,
                        lens_id=asset.lens_id,
                        attempts=attempt + 1
                    )
                    return True

            # QC failed - build correction prompt
            if attempt < MAX_QC_RETRIES:
                prompt = self.qc_service.build_correction_prompt(prompt, qc_result)
                logger.info(
                    "qc_failed_retrying",
                    scene_id=scene.scene_id,
                    lens_id=asset.lens_id,
                    issues=qc_result.issues
                )

        # All retries failed
        asset.status = AssetStatus.FAILED
        session.add(asset)
        await session.commit()

        logger.error(
            "lens_generation_failed",
            scene_id=scene.scene_id,
            lens_id=asset.lens_id,
            attempts=asset.attempts
        )
        return False

    def _build_response(self, scene: FlashbackScene) -> FlashbackResponse:
        """Build API response from scene data."""
        sources = [
            Source(label="Wikipedia", url=scene.wikipedia_url),
            Source(
                label="On this Day",
                url=f"https://en.wikipedia.org/wiki/Wikipedia:On_this_day/Today"
            )
        ]

        lenses = []
        for asset in sorted(scene.assets, key=lambda a: a.lens_id):
            lenses.append(Lens(
                lens_id=asset.lens_id,
                name=asset.lens_name,
                image_url=asset.image_url
            ))

        scene_response = SceneResponse(
            scene_id=scene.scene_id,
            date=scene.date,
            title=scene.event_title,
            year=scene.event_year,
            summary=scene.event_summary,
            sources=sources,
            lenses=lenses
        )

        return FlashbackResponse(
            status=scene.status.value,
            scene=scene_response
        )

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text[:50].strip("-")


# Factory function
async def get_flashback_service() -> FlashbackService:
    """Create a FlashbackService with all dependencies."""
    wikimedia = await get_wikimedia_service()
    image_service = get_image_service()
    qc_service = get_qc_service()

    return FlashbackService(wikimedia, image_service, qc_service)
