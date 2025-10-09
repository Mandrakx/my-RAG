"""
Tests for transcript normalizer
"""

import pytest
from datetime import datetime
from src.ingestion.normalizer import TranscriptNormalizer


@pytest.fixture
def normalizer():
    return TranscriptNormalizer()


@pytest.mark.asyncio
async def test_normalize_structured_transcript(normalizer):
    """Test normalizing structured transcript with segments"""

    transcript_data = {
        "metadata": {
            "job_id": "test-job-123",
            "timestamp": "2025-10-10T10:00:00Z",
            "duration_seconds": 120.5,
            "language": "fr",
            "audio_filename": "test.m4a"
        },
        "segments": [
            {
                "speaker": "John",
                "text": "Hello, how are you?",
                "start_time": 0.0,
                "end_time": 2.5,
                "confidence": 0.95
            },
            {
                "speaker": "Marie",
                "text": "I'm doing well, thanks!",
                "start_time": 2.5,
                "end_time": 5.0,
                "confidence": 0.92
            }
        ]
    }

    result = await normalizer.normalize(transcript_data)

    # Check metadata
    assert result['metadata']['job_id'] == "test-job-123"
    assert result['metadata']['duration_seconds'] == 120.5
    assert result['metadata']['language'] == "fr"

    # Check turns
    assert len(result['turns']) == 2
    assert result['turns'][0]['speaker'] == "John"
    assert result['turns'][0]['text'] == "Hello, how are you?"
    assert result['turns'][0]['turn'] == 0

    # Check participants
    assert len(result['participants']) == 2
    speakers = [p['speaker'] for p in result['participants']]
    assert "John" in speakers
    assert "Marie" in speakers

    # Check statistics
    assert result['statistics']['total_turns'] == 2
    assert result['statistics']['total_speakers'] == 2
    assert result['statistics']['avg_confidence'] == pytest.approx(0.935, 0.01)


@pytest.mark.asyncio
async def test_normalize_text_transcript(normalizer):
    """Test normalizing plain text transcript"""

    transcript_data = {
        "metadata": {
            "job_id": "test-job-456",
            "timestamp": "2025-10-10T11:00:00Z"
        },
        "transcript": """Alice: Bonjour, comment ça va?
Bob: Très bien merci, et toi?
Alice: Ça va bien aussi."""
    }

    result = await normalizer.normalize(transcript_data)

    # Check turns
    assert len(result['turns']) == 3
    assert result['turns'][0]['speaker'] == "Alice"
    assert result['turns'][0]['text'] == "Bonjour, comment ça va?"
    assert result['turns'][1]['speaker'] == "Bob"

    # Check participants
    assert len(result['participants']) == 2


def test_normalize_speaker_names(normalizer):
    """Test speaker name normalization"""

    assert normalizer._normalize_speaker("Speaker 1") == "Speaker"
    assert normalizer._normalize_speaker("speaker1") == "Speaker"
    assert normalizer._normalize_speaker("John Doe") == "John Doe"
    assert normalizer._normalize_speaker("unknown") == "Speaker"
    assert normalizer._normalize_speaker("Locuteur 1") == "Locuteur"


def test_parse_text_turns(normalizer):
    """Test parsing turns from plain text"""

    text = """John: Hello everyone
Marie: Hi John!
John: How are you doing?"""

    turns = normalizer._parse_text_turns(text)

    assert len(turns) == 3
    assert turns[0]['speaker'] == "John"
    assert turns[0]['text'] == "Hello everyone"
    assert turns[1]['speaker'] == "Marie"
    assert turns[2]['speaker'] == "John"
    assert turns[2]['text'] == "How are you doing?"


def test_to_jsonl_conversion(normalizer):
    """Test conversion to JSONL format"""

    conversation = {
        'metadata': {
            'job_id': 'test-123',
            'date': '2025-10-10T10:00:00Z',
            'duration_seconds': 60,
            'language': 'fr'
        },
        'turns': [
            {'turn': 0, 'speaker': 'Alice', 'text': 'Hello', 'timestamp_ms': None, 'confidence': None}
        ],
        'participants': [
            {'speaker': 'Alice', 'role': 'participant', 'turn_count': 1}
        ],
        'statistics': {
            'total_turns': 1,
            'total_speakers': 1,
            'avg_confidence': None
        }
    }

    jsonl = normalizer.to_jsonl(conversation)

    assert 'metadata' in jsonl
    assert 'test-123' in jsonl
    assert 'Alice' in jsonl
    assert '\n' in jsonl  # Multiple lines


def test_from_jsonl_conversion(normalizer):
    """Test parsing JSONL back to conversation"""

    jsonl_content = '''{"type": "metadata", "job_id": "test-123", "date": "2025-10-10T10:00:00Z"}
{"type": "turn", "turn": 0, "speaker": "Alice", "text": "Hello"}
{"type": "participants", "data": [{"speaker": "Alice"}]}
{"type": "statistics", "total_turns": 1}'''

    conversation = normalizer.from_jsonl(jsonl_content)

    assert conversation['metadata']['job_id'] == "test-123"
    assert len(conversation['turns']) == 1
    assert conversation['turns'][0]['speaker'] == "Alice"


def test_calculate_avg_confidence(normalizer):
    """Test average confidence calculation"""

    turns_with_confidence = [
        {'confidence': 0.9},
        {'confidence': 0.8},
        {'confidence': 0.95}
    ]

    avg = normalizer._calculate_avg_confidence(turns_with_confidence)
    assert avg == pytest.approx(0.883, 0.01)

    # Test with None values
    turns_with_none = [
        {'confidence': 0.9},
        {'confidence': None},
        {'confidence': 0.8}
    ]

    avg = normalizer._calculate_avg_confidence(turns_with_none)
    assert avg == pytest.approx(0.85, 0.01)

    # Test all None
    turns_all_none = [
        {'confidence': None},
        {'confidence': None}
    ]

    avg = normalizer._calculate_avg_confidence(turns_all_none)
    assert avg is None
