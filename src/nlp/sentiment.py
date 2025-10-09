"""
Sentiment analysis for conversation turns
Detects emotions and sentiment in dialogue
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

logger = logging.getLogger(__name__)


class SentimentLabel(str, Enum):
    """Sentiment labels"""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class EmotionLabel(str, Enum):
    """Emotion labels"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    text: str
    sentiment: SentimentLabel
    score: float
    stars: int  # 1-5 rating
    emotion: Optional[EmotionLabel] = None
    emotion_score: float = 0.0


class SentimentAnalyzer:
    """
    Analyze sentiment of conversation turns
    Supports multilingual sentiment detection
    """

    def __init__(
        self,
        model_name: str = "nlptown/bert-base-multilingual-uncased-sentiment",
        device: str = "cuda",
        batch_size: int = 24
    ):
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.batch_size = batch_size

        self._load_model()

        logger.info(f"Initialized SentimentAnalyzer: {model_name}, device: {self.device}")

    def _load_model(self):
        """Load sentiment analysis model"""
        logger.info(f"Loading sentiment model: {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        self.model.to(self.device)
        self.model.eval()

        # Create pipeline
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1,
            top_k=None  # Return all scores
        )

        logger.info("Sentiment model loaded successfully")

    def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text

        Args:
            text: Input text

        Returns:
            SentimentResult
        """
        # Run sentiment analysis
        results = self.sentiment_pipeline(text)[0]

        # Parse results (model returns star ratings 1-5)
        stars_scores = {}
        for result in results:
            # Extract star rating from label (e.g., "1 star", "5 stars")
            label = result['label']
            stars = int(label.split()[0])
            stars_scores[stars] = result['score']

        # Get predicted rating
        predicted_stars = max(stars_scores.keys(), key=lambda x: stars_scores[x])
        confidence = stars_scores[predicted_stars]

        # Map to sentiment label
        sentiment = self._stars_to_sentiment(predicted_stars)

        return SentimentResult(
            text=text,
            sentiment=sentiment,
            score=confidence,
            stars=predicted_stars
        )

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment for multiple texts in batch

        Args:
            texts: List of texts

        Returns:
            List of SentimentResult
        """
        results = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            batch_results = self.sentiment_pipeline(batch)

            for text, result in zip(batch, batch_results):
                # Parse star ratings
                stars_scores = {
                    int(r['label'].split()[0]): r['score']
                    for r in result
                }

                predicted_stars = max(stars_scores.keys(), key=lambda x: stars_scores[x])
                confidence = stars_scores[predicted_stars]

                sentiment = self._stars_to_sentiment(predicted_stars)

                results.append(
                    SentimentResult(
                        text=text,
                        sentiment=sentiment,
                        score=confidence,
                        stars=predicted_stars
                    )
                )

        return results

    def analyze_conversation(
        self,
        turns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment for all turns in conversation

        Args:
            turns: List of conversation turns

        Returns:
            Dict with turn sentiments and conversation-level stats
        """
        texts = [turn.get('text', '') for turn in turns if turn.get('text')]

        if not texts:
            return {'turn_sentiments': [], 'stats': {}}

        # Analyze all turns
        sentiments = self.analyze_batch(texts)

        # Calculate conversation-level statistics
        stars = [s.stars for s in sentiments]
        avg_stars = sum(stars) / len(stars)

        # Count sentiment distribution
        sentiment_counts = {}
        for s in sentiments:
            sentiment_counts[s.sentiment.value] = sentiment_counts.get(s.sentiment.value, 0) + 1

        # Identify sentiment shifts
        shifts = []
        for i in range(1, len(sentiments)):
            prev = sentiments[i-1]
            curr = sentiments[i]

            # Detect significant shift (2+ stars difference)
            if abs(prev.stars - curr.stars) >= 2:
                shifts.append({
                    'turn': i,
                    'from': prev.sentiment.value,
                    'to': curr.sentiment.value,
                    'from_stars': prev.stars,
                    'to_stars': curr.stars
                })

        return {
            'turn_sentiments': [
                {
                    'turn': i,
                    'text': s.text,
                    'sentiment': s.sentiment.value,
                    'stars': s.stars,
                    'score': s.score
                }
                for i, s in enumerate(sentiments)
            ],
            'stats': {
                'avg_stars': avg_stars,
                'overall_sentiment': self._stars_to_sentiment(round(avg_stars)).value,
                'distribution': sentiment_counts,
                'sentiment_shifts': shifts,
                'num_positive': sum(1 for s in sentiments if s.stars >= 4),
                'num_negative': sum(1 for s in sentiments if s.stars <= 2),
                'num_neutral': sum(1 for s in sentiments if s.stars == 3)
            }
        }

    def _stars_to_sentiment(self, stars: int) -> SentimentLabel:
        """Map star rating to sentiment label"""
        if stars == 1:
            return SentimentLabel.VERY_NEGATIVE
        elif stars == 2:
            return SentimentLabel.NEGATIVE
        elif stars == 3:
            return SentimentLabel.NEUTRAL
        elif stars == 4:
            return SentimentLabel.POSITIVE
        else:  # 5
            return SentimentLabel.VERY_POSITIVE

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'batch_size': self.batch_size
        }


class EmotionAnalyzer:
    """
    Analyze emotions in conversation
    Uses emotion classification models
    """

    def __init__(
        self,
        model_name: str = "j-hartmann/emotion-english-distilroberta-base",
        device: str = "cuda"
    ):
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"

        self._load_model()

        logger.info(f"Initialized EmotionAnalyzer: {model_name}")

    def _load_model(self):
        """Load emotion classification model"""
        logger.info(f"Loading emotion model: {self.model_name}")

        self.emotion_pipeline = pipeline(
            "text-classification",
            model=self.model_name,
            device=0 if self.device == "cuda" else -1,
            top_k=None
        )

    def analyze_emotions(self, text: str) -> Dict[str, float]:
        """
        Analyze emotions in text

        Args:
            text: Input text

        Returns:
            Dict mapping emotion labels to scores
        """
        results = self.emotion_pipeline(text)[0]

        emotions = {}
        for result in results:
            emotion = result['label'].lower()
            score = result['score']
            emotions[emotion] = score

        return emotions

    def get_dominant_emotion(self, text: str) -> tuple[str, float]:
        """Get dominant emotion and its score"""
        emotions = self.analyze_emotions(text)
        dominant = max(emotions.items(), key=lambda x: x[1])
        return dominant


def analyze_conversation_mood(
    turns: List[Dict[str, Any]],
    sentiment_analyzer: SentimentAnalyzer
) -> Dict[str, Any]:
    """
    Comprehensive mood analysis for conversation

    Returns:
        Mood profile with sentiment trajectory and key moments
    """
    analysis = sentiment_analyzer.analyze_conversation(turns)

    # Identify key moments
    turn_sentiments = analysis['turn_sentiments']

    # Find most positive moment
    most_positive = max(turn_sentiments, key=lambda x: x['stars'])

    # Find most negative moment
    most_negative = min(turn_sentiments, key=lambda x: x['stars'])

    # Calculate sentiment trajectory (start vs end)
    if len(turn_sentiments) >= 2:
        start_avg = sum(t['stars'] for t in turn_sentiments[:3]) / min(3, len(turn_sentiments))
        end_avg = sum(t['stars'] for t in turn_sentiments[-3:]) / min(3, len(turn_sentiments))

        trajectory = {
            'start_sentiment': start_avg,
            'end_sentiment': end_avg,
            'trend': 'improving' if end_avg > start_avg else 'declining' if end_avg < start_avg else 'stable'
        }
    else:
        trajectory = {'trend': 'insufficient_data'}

    return {
        **analysis,
        'key_moments': {
            'most_positive': {
                'turn': most_positive['turn'],
                'text': most_positive['text'],
                'stars': most_positive['stars']
            },
            'most_negative': {
                'turn': most_negative['turn'],
                'text': most_negative['text'],
                'stars': most_negative['stars']
            }
        },
        'trajectory': trajectory
    }


if __name__ == "__main__":
    # Test sentiment analysis
    logging.basicConfig(level=logging.INFO)

    analyzer = SentimentAnalyzer(device="cuda")

    test_texts = [
        "C'est absolument merveilleux!",
        "Je suis très déçu par ce résultat.",
        "C'est normal, rien de spécial."
    ]

    results = analyzer.analyze_batch(test_texts)

    for text, result in zip(test_texts, results):
        print(f"\nText: {text}")
        print(f"Sentiment: {result.sentiment.value}")
        print(f"Stars: {result.stars}")
        print(f"Confidence: {result.score:.2f}")
