"""SceneSpec generator - deterministic transform from Wikimedia sources."""
import re
import structlog
from typing import Optional
from app.models.schemas import SceneSpec, LocationSpec, SettingSpec
from app.services.wikimedia import WikimediaService

logger = structlog.get_logger()

# Era cue mappings by decade
ERA_CUES = {
    range(1900, 1920): ["gas lamps", "horse carriages", "early automobiles", "top hats", "long dresses"],
    range(1920, 1940): ["art deco", "flapper dresses", "early radio", "jazz age fashion", "Model T cars"],
    range(1940, 1950): ["WWII era", "military uniforms", "wartime posters", "victory gardens", "radio broadcasts"],
    range(1950, 1960): ["post-war optimism", "poodle skirts", "chrome cars", "early television", "suburban homes"],
    range(1960, 1970): ["civil rights era", "space race", "mod fashion", "color TV", "muscle cars"],
    range(1970, 1980): ["disco era", "bell bottoms", "protest movements", "analog technology", "wood paneling"],
    range(1980, 1990): ["neon colors", "big hair", "early computers", "brick phones", "synthesizers"],
    range(1990, 2000): ["grunge fashion", "early internet", "CRT monitors", "chunky phones", "CD players"],
    range(2000, 2010): ["Y2K aesthetic", "flip phones", "iPods", "flat screens", "SUVs"],
    range(2010, 2020): ["smartphones", "social media era", "minimalist design", "electric cars", "LED screens"],
}

# Mood keywords mapping
MOOD_KEYWORDS = {
    "tense": ["war", "conflict", "battle", "crisis", "attack", "invasion", "tension", "standoff"],
    "hopeful": ["peace", "treaty", "agreement", "discovery", "breakthrough", "achievement", "first"],
    "somber": ["death", "funeral", "disaster", "tragedy", "assassination", "memorial", "loss"],
    "celebratory": ["victory", "celebration", "independence", "wedding", "coronation", "win", "champion"],
    "uncertain": ["election", "trial", "referendum", "debate", "controversy", "scandal"]
}

# Role extraction keywords
ROLE_KEYWORDS = {
    "soldiers": ["military", "army", "war", "battle", "troops", "forces"],
    "scientists": ["scientist", "research", "laboratory", "discovery", "experiment"],
    "politicians": ["president", "prime minister", "congress", "parliament", "senator", "election"],
    "protesters": ["protest", "demonstration", "march", "rally", "movement"],
    "athletes": ["championship", "olympic", "game", "match", "tournament", "race"],
    "crowd": ["gathered", "assembled", "witnessed", "watched", "attended"],
    "journalists": ["press", "reporter", "media", "broadcast", "news"],
    "delegates": ["summit", "conference", "treaty", "agreement", "negotiation"]
}


class SceneSpecGenerator:
    """
    Generates SceneSpec from Wikimedia source data.

    The SceneSpec is the truth contract that drives all image generation.
    It must be deterministic - same input always produces same output.
    """

    def __init__(self, wikimedia: WikimediaService):
        self.wikimedia = wikimedia

    async def generate(
        self,
        event: dict,
        wikidata: Optional[dict] = None,
        extract: Optional[str] = None
    ) -> SceneSpec:
        """
        Generate a SceneSpec from OnThisDay event data.

        Args:
            event: OnThisDay event with text, year, and pages
            wikidata: Optional Wikidata structured data
            extract: Optional Wikipedia article extract

        Returns:
            SceneSpec with all fields populated
        """
        event_text = event.get("text", "")
        year = event.get("year", 0)
        primary_page = event.get("primary_page", event.get("pages", [{}])[0])
        title = primary_page.get("title", event_text[:100])

        # Combine text sources for analysis
        full_text = f"{event_text} {extract or ''}"

        # Extract location
        location = self._extract_location(full_text, wikidata)

        # Determine setting
        setting = self._determine_setting(full_text)

        # Get era cues
        era_cues = self._get_era_cues(year)

        # Extract roles
        roles = self._extract_roles(full_text)

        # Extract key objects
        key_objects = self._extract_key_objects(full_text, year)

        # Determine mood
        mood = self._determine_mood(full_text)

        # Build must_include list
        must_include = self._build_must_include(event_text, key_objects, location)

        spec = SceneSpec(
            event_title=title,
            year=year,
            location=location,
            setting=setting,
            era_cues=era_cues,
            roles=roles,
            key_objects=key_objects,
            mood=mood,
            must_include=must_include
        )

        logger.info(
            "generated_scene_spec",
            title=title,
            year=year,
            mood=mood,
            roles=roles,
            key_objects=key_objects[:3]
        )

        return spec

    def _extract_location(self, text: str, wikidata: Optional[dict]) -> LocationSpec:
        """Extract location from text and Wikidata."""
        name = "Unknown location"
        coords = [0.0, 0.0]

        # Try Wikidata first
        if wikidata and wikidata.get("location"):
            loc = wikidata["location"]
            coords = [loc.get("latitude", 0.0), loc.get("longitude", 0.0)]

        # Extract location name from text
        location_patterns = [
            r"in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z][a-z]+)*)",
            r"at ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+(?:United States|UK|France|Germany|Japan|China|Russia)"
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                break

        return LocationSpec(name=name, coords=coords)

    def _determine_setting(self, text: str) -> SettingSpec:
        """Determine indoor/outdoor setting and time of day."""
        text_lower = text.lower()

        # Indoor indicators
        indoor_words = ["parliament", "congress", "court", "office", "building", "room",
                       "hall", "theater", "theatre", "museum", "laboratory", "church"]

        # Outdoor indicators
        outdoor_words = ["field", "street", "square", "beach", "ocean", "mountain",
                        "park", "garden", "stadium", "battlefield", "march"]

        indoor_score = sum(1 for w in indoor_words if w in text_lower)
        outdoor_score = sum(1 for w in outdoor_words if w in text_lower)

        if indoor_score > outdoor_score:
            environment = "indoor"
        elif outdoor_score > indoor_score:
            environment = "outdoor"
        else:
            environment = "mixed"

        # Time of day (default to day unless night indicators present)
        night_words = ["night", "evening", "midnight", "dawn", "dusk"]
        time_of_day = "night" if any(w in text_lower for w in night_words) else "day"

        return SettingSpec(environment=environment, time_of_day=time_of_day)

    def _get_era_cues(self, year: int) -> list[str]:
        """Get era-appropriate visual cues for the year."""
        for year_range, cues in ERA_CUES.items():
            if year in year_range:
                return cues

        # Ancient/medieval fallback
        if year < 1900:
            if year < 1500:
                return ["medieval architecture", "candlelight", "manuscripts", "stone buildings"]
            else:
                return ["colonial era", "sailing ships", "quill pens", "oil lamps", "horse-drawn transport"]

        # Future fallback (shouldn't happen)
        return ["modern setting", "contemporary architecture"]

    def _extract_roles(self, text: str) -> list[str]:
        """Extract relevant human roles from the event text."""
        text_lower = text.lower()
        roles = []

        for role, keywords in ROLE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                roles.append(role)

        # Always include crowd as fallback
        if not roles:
            roles = ["crowd"]

        return roles[:5]  # Limit to 5 roles

    def _extract_key_objects(self, text: str, year: int) -> list[str]:
        """Extract key objects that should appear in images."""
        text_lower = text.lower()
        objects = []

        # Document/paper related
        if any(w in text_lower for w in ["signed", "treaty", "declaration", "constitution", "document"]):
            objects.append("historical document with period-appropriate paper")

        # Technology
        if "telephone" in text_lower or "phone" in text_lower:
            if year < 1980:
                objects.append("rotary telephone")
            elif year < 2007:
                objects.append("mobile phone of the era")

        if "computer" in text_lower:
            if year < 1985:
                objects.append("mainframe computer with tape reels")
            elif year < 2000:
                objects.append("CRT monitor and keyboard")
            else:
                objects.append("flat screen computer")

        # Transportation
        if any(w in text_lower for w in ["airplane", "aircraft", "flight"]):
            objects.append("period-appropriate aircraft")

        if any(w in text_lower for w in ["ship", "vessel", "boat"]):
            objects.append("period-appropriate vessel")

        # Space
        if any(w in text_lower for w in ["space", "rocket", "moon", "satellite"]):
            objects.append("space equipment of the era")

        # Military
        if any(w in text_lower for w in ["military", "army", "war", "battle"]):
            objects.append("period-appropriate military equipment")

        # Sports
        if any(w in text_lower for w in ["championship", "olympic", "game", "match"]):
            objects.append("sports equipment")

        # Fallback - era-appropriate props
        if not objects:
            if year < 1950:
                objects.append("period newspapers")
            else:
                objects.append("era-appropriate technology")

        return objects[:5]

    def _determine_mood(self, text: str) -> str:
        """Determine the emotional mood of the event."""
        text_lower = text.lower()

        mood_scores = {}
        for mood, keywords in MOOD_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            mood_scores[mood] = score

        # Return highest scoring mood, or uncertain if tied/none
        if max(mood_scores.values()) == 0:
            return "uncertain"

        return max(mood_scores.keys(), key=lambda m: mood_scores[m])

    def _build_must_include(
        self,
        event_text: str,
        key_objects: list[str],
        location: LocationSpec
    ) -> list[str]:
        """Build the must_include list for image generation."""
        must_include = []

        # Add location if known
        if location.name != "Unknown location":
            must_include.append(f"visual reference to {location.name}")

        # Add primary key object
        if key_objects:
            must_include.append(key_objects[0])

        # Add human presence indicator
        must_include.append("period-appropriate clothing on figures")

        return must_include[:5]
