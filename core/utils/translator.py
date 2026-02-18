"""
Local offline Tamil-to-English translator using Helsinki-NLP/opus-mt-ta-en.
Improves multilingual retrieval by translating non-English queries to English
before embedding generation. Fully offline after first model download.
"""

from transformers import MarianMTModel, MarianTokenizer
from core.logger import get_logger

logger = get_logger(__name__)


class Translator:
    """
    Tamil-to-English translator using Helsinki-NLP/opus-mt-ta-en.
    
    Model is loaded once at startup and reused for all translations.
    """

    def __init__(self):
        """Initialize translator model (downloads on first run, then cached locally)."""
        logger.info("Loading Tamil-English translation model...")
        
        try:
            self.model_name = "Helsinki-NLP/opus-mt-mul-en"
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            self.model = MarianMTModel.from_pretrained(self.model_name)
            
            logger.info("Tamil-English translation model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load translation model: {e}", exc_info=True)
            raise

    def needs_translation(self, text: str) -> bool:
        """
        Check if text contains non-ASCII characters (likely non-English).
        
        Args:
            text: Input text to check
            
        Returns:
            True if text contains non-ASCII characters
        """
        return not all(ord(c) < 128 for c in text)

    def translate(self, text: str) -> str:
        """
        Translate Tamil text to English.
        
        Args:
            text: Tamil query text
            
        Returns:
            English translation or original text if translation fails
        """
        if not text or not text.strip():
            return text

        try:
            # Check if translation is needed
            if not self.needs_translation(text):
                logger.debug(f"Text is ASCII - no translation needed: {text[:50]}...")
                return text

            # Tokenize input
            inputs = self.tokenizer(text, return_tensors="pt", padding=True)

            # Generate translation
            translated_tokens = self.model.generate(**inputs)

            # Decode translation
            translated_text = self.tokenizer.decode(
                translated_tokens[0],
                skip_special_tokens=True
            )

            logger.info(f"[TRANSLATE] Original ({len(text)} chars): {text[:50]}...")
            logger.info(f"[TRANSLATE] Translated: {translated_text[:80]}...")

            return translated_text

        except Exception as e:
            logger.error(f"Translation failed: {e}", exc_info=True)
            # Return original text if translation fails
            return text
