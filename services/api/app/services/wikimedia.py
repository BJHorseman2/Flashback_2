"""Wikimedia API integration for OnThisDay events and pageviews."""
import httpx
from datetime import datetime, timedelta
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()

WIKIMEDIA_REST_BASE = "https://api.wikimedia.org/feed/v1/wikipedia"
WIKIPEDIA_API_BASE = "https://en.wikipedia.org/api/rest_v1"
PAGEVIEWS_API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
WIKIDATA_API_BASE = "https://www.wikidata.org/w/api.php"

USER_AGENT = "FlashbackDaily/1.0 (https://flashbackdaily.app; contact@flashbackdaily.app)"


class WikimediaService:
    """Service for fetching data from Wikimedia APIs."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_on_this_day_events(self, month: int, day: int, lang: str = "en") -> list[dict]:
        """
        Fetch events that happened on this day from Wikimedia Feed API.

        API: GET /feed/v1/wikipedia/{lang}/onthisday/events/{MM}/{DD}
        """
        url = f"{WIKIMEDIA_REST_BASE}/{lang}/onthisday/events/{month:02d}/{day:02d}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            events = data.get("events", [])
            logger.info("fetched_on_this_day", count=len(events), month=month, day=day)
            return events

        except httpx.HTTPStatusError as e:
            logger.warning("on_this_day_api_error", status=e.response.status_code, url=url)
            # Fallback: try Wikipedia REST API directly
            return await self._fallback_on_this_day(month, day, lang)

    async def _fallback_on_this_day(self, month: int, day: int, lang: str = "en") -> list[dict]:
        """Fallback method using Wikipedia REST API."""
        url = f"https://{lang}.wikipedia.org/api/rest_v1/feed/onthisday/events/{month:02d}/{day:02d}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("events", [])
        except Exception as e:
            logger.error("fallback_on_this_day_failed", error=str(e))
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_pageviews(
        self,
        article_title: str,
        days: int = 30,
        lang: str = "en"
    ) -> Optional[int]:
        """
        Get pageviews for a Wikipedia article over the last N days.

        Note: Pageviews API only has data from July 1, 2015.
        """
        article_title_encoded = article_title.replace(" ", "_")
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        url = (
            f"{PAGEVIEWS_API_BASE}/per-article/{lang}.wikipedia/all-access/all-agents/"
            f"{article_title_encoded}/daily/{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            total_views = sum(item.get("views", 0) for item in data.get("items", []))
            logger.info("fetched_pageviews", article=article_title, views=total_views, days=days)
            return total_views

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info("pageviews_not_found", article=article_title)
                return None
            logger.warning("pageviews_api_error", status=e.response.status_code, article=article_title)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_wikidata_info(self, title: str, lang: str = "en") -> Optional[dict]:
        """
        Get Wikidata information for a Wikipedia article.

        Returns QID, sitelinks count, and structured data.
        """
        params = {
            "action": "wbgetentities",
            "sites": f"{lang}wiki",
            "titles": title,
            "format": "json",
            "props": "sitelinks|labels|descriptions|claims"
        }

        try:
            response = await self.client.get(WIKIDATA_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()

            entities = data.get("entities", {})
            if not entities:
                return None

            # Get first entity (there should only be one)
            qid = next(iter(entities.keys()))
            if qid == "-1":
                return None

            entity = entities[qid]
            sitelinks = entity.get("sitelinks", {})

            # Extract location if available (P625 = coordinate location)
            claims = entity.get("claims", {})
            location = None
            if "P625" in claims:
                coord_claim = claims["P625"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if coord_claim:
                    location = {
                        "latitude": coord_claim.get("latitude"),
                        "longitude": coord_claim.get("longitude")
                    }

            # Extract country (P17)
            country = None
            if "P17" in claims:
                country_claim = claims["P17"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                country_qid = country_claim.get("id")
                if country_qid:
                    country = country_qid

            result = {
                "qid": qid,
                "sitelinks_count": len(sitelinks),
                "location": location,
                "country_qid": country,
                "labels": entity.get("labels", {}),
                "descriptions": entity.get("descriptions", {})
            }

            logger.info("fetched_wikidata", title=title, qid=qid, sitelinks=len(sitelinks))
            return result

        except Exception as e:
            logger.warning("wikidata_fetch_error", title=title, error=str(e))
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_article_extract(self, title: str, lang: str = "en") -> Optional[str]:
        """Get the lead section extract of a Wikipedia article."""
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            extract = data.get("extract", "")
            logger.info("fetched_extract", title=title, length=len(extract))
            return extract

        except Exception as e:
            logger.warning("extract_fetch_error", title=title, error=str(e))
            return None


# Singleton instance
_wikimedia_service: Optional[WikimediaService] = None


async def get_wikimedia_service() -> WikimediaService:
    """Get or create the Wikimedia service instance."""
    global _wikimedia_service
    if _wikimedia_service is None:
        _wikimedia_service = WikimediaService()
    return _wikimedia_service
