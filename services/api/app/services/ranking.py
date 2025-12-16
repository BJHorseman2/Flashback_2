"""Event ranking service - selects the most culturally significant event."""
import structlog
from typing import Optional
from app.services.wikimedia import WikimediaService
from app.models.schemas import RankSignals

logger = structlog.get_logger()


class EventRankingService:
    """
    Ranks events by cultural significance using Wikimedia signals.

    Ranking algorithm:
    1. Primary: Pageviews (last 30 days) - works for events with modern Wikipedia pages
    2. Fallback (pre-2015 or missing data):
       - Wikidata sitelinks count × 10
       - Article lede length / 200
    """

    def __init__(self, wikimedia: WikimediaService):
        self.wikimedia = wikimedia

    async def rank_events(self, events: list[dict], lang: str = "en") -> list[dict]:
        """
        Rank a list of OnThisDay events by cultural significance.

        Returns events sorted by score (highest first) with rank_signals attached.
        """
        ranked_events = []

        for event in events:
            pages = event.get("pages", [])
            if not pages:
                continue

            # Use the first/primary page for the event
            primary_page = pages[0]
            title = primary_page.get("title", "")

            if not title:
                continue

            signals = await self._calculate_signals(title, lang)

            ranked_events.append({
                **event,
                "primary_page": primary_page,
                "rank_signals": signals,
                "score": signals.final_score
            })

        # Sort by score descending
        ranked_events.sort(key=lambda e: e["score"], reverse=True)

        logger.info(
            "ranked_events",
            total=len(events),
            ranked=len(ranked_events),
            top_score=ranked_events[0]["score"] if ranked_events else 0
        )

        return ranked_events

    async def _calculate_signals(self, title: str, lang: str = "en") -> RankSignals:
        """Calculate ranking signals for an article."""
        signals = RankSignals()

        # Try to get pageviews (primary signal)
        pageviews_30d = await self.wikimedia.get_pageviews(title, days=30, lang=lang)
        pageviews_365d = await self.wikimedia.get_pageviews(title, days=365, lang=lang)

        signals.pageviews_30d = pageviews_30d
        signals.pageviews_365d = pageviews_365d

        # Get Wikidata info for fallback signals
        wikidata = await self.wikimedia.get_wikidata_info(title, lang=lang)

        if wikidata:
            signals.sitelinks_count = wikidata.get("sitelinks_count", 0)

        # Get article extract for lede length
        extract = await self.wikimedia.get_article_extract(title, lang=lang)
        if extract:
            signals.lede_length = len(extract)

        # Calculate final score
        signals.final_score = self._compute_score(signals)

        return signals

    def _compute_score(self, signals: RankSignals) -> float:
        """
        Compute final ranking score from signals.

        Pageviews are the primary signal when available.
        Falls back to sitelinks and lede length for older events.
        """
        score = 0.0

        # Primary: Pageviews (if available)
        if signals.pageviews_30d is not None and signals.pageviews_30d > 0:
            # Use 30-day pageviews as primary score
            score = float(signals.pageviews_30d)

            # Boost with 365-day data if available (for seasonal events)
            if signals.pageviews_365d:
                # Add 10% of yearly views to account for events with seasonal interest
                score += signals.pageviews_365d * 0.1
        else:
            # Fallback scoring for pre-2015 or missing data
            if signals.sitelinks_count:
                score += signals.sitelinks_count * 10

            if signals.lede_length:
                score += signals.lede_length / 200

        return score

    async def select_top_event(self, events: list[dict], lang: str = "en") -> Optional[dict]:
        """
        Select the single most significant event from a list.

        Returns the top-ranked event with all metadata attached.
        """
        ranked = await self.rank_events(events, lang)

        if not ranked:
            return None

        top = ranked[0]
        logger.info(
            "selected_top_event",
            title=top["primary_page"].get("title"),
            year=top.get("year"),
            score=top["score"]
        )

        return top
