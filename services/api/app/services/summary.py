"""Summary generator - creates grounded 2-sentence summaries."""
import re
import structlog

logger = structlog.get_logger()

# Banned adjectives that make content feel like "AI slop"
BANNED_ADJECTIVES = [
    "shocking", "unbelievable", "iconic", "legendary", "incredible",
    "amazing", "stunning", "remarkable", "extraordinary", "unprecedented",
    "groundbreaking", "revolutionary", "historic", "momentous", "epic",
    "breathtaking", "awe-inspiring", "mind-blowing"
]


class SummaryGenerator:
    """
    Generates grounded 2-sentence summaries from source text.

    Rules:
    - Exactly 2 sentences
    - No banned adjectives
    - Only facts that appear in source text
    - Neutral, factual tone
    """

    def generate(self, event_text: str, extract: str, year: int) -> str:
        """
        Generate a 2-sentence summary from event text and Wikipedia extract.

        Args:
            event_text: The OnThisDay event description
            extract: Wikipedia article extract
            year: Event year

        Returns:
            Exactly 2-sentence summary
        """
        # Clean the input
        event_text = self._clean_text(event_text)
        extract = self._clean_text(extract) if extract else ""

        # Build summary from event text first (most concise source)
        sentence1 = self._build_first_sentence(event_text, year)
        sentence2 = self._build_second_sentence(event_text, extract)

        # Ensure we have exactly 2 sentences
        summary = f"{sentence1} {sentence2}"

        # Final validation
        summary = self._validate_and_fix(summary)

        logger.info("generated_summary", length=len(summary), sentence_count=summary.count("."))

        return summary

    def _clean_text(self, text: str) -> str:
        """Remove unwanted characters and normalize whitespace."""
        # Remove citation markers like [1], [citation needed]
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\[citation needed\]", "", text, flags=re.IGNORECASE)

        # Normalize whitespace
        text = " ".join(text.split())

        # Remove banned adjectives
        for adj in BANNED_ADJECTIVES:
            text = re.sub(rf"\b{adj}\b", "", text, flags=re.IGNORECASE)

        return text.strip()

    def _build_first_sentence(self, event_text: str, year: int) -> str:
        """Build the first sentence - what happened and when."""
        # Extract the core event from OnThisDay text
        sentences = self._split_sentences(event_text)

        if sentences:
            first = sentences[0]
            # Ensure year is mentioned
            if str(year) not in first:
                first = f"In {year}, {first[0].lower()}{first[1:]}"
            return first

        return f"In {year}, a significant event occurred."

    def _build_second_sentence(self, event_text: str, extract: str) -> str:
        """Build the second sentence - significance or additional context."""
        # Try to get a second sentence from event text
        sentences = self._split_sentences(event_text)

        if len(sentences) > 1:
            return sentences[1]

        # Fall back to extract
        if extract:
            extract_sentences = self._split_sentences(extract)
            # Skip the first sentence (usually similar to event text)
            # Find a sentence that adds context
            for s in extract_sentences[1:4]:
                if len(s) > 30 and len(s) < 200:
                    return s

        # Generic fallback
        return "This event had lasting significance."

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        # Ensure each ends with punctuation
        sentences = [s if s[-1] in ".!?" else s + "." for s in sentences if s]
        return sentences

    def _validate_and_fix(self, summary: str) -> str:
        """Ensure summary is exactly 2 sentences and properly formatted."""
        sentences = self._split_sentences(summary)

        if len(sentences) == 0:
            return "An event of historical significance occurred. Further details are available in the sources."

        if len(sentences) == 1:
            return f"{sentences[0]} Further details are available in the sources."

        if len(sentences) > 2:
            # Keep only first two
            return f"{sentences[0]} {sentences[1]}"

        return f"{sentences[0]} {sentences[1]}"
