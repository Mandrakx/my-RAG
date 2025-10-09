"""
Intelligent conversation chunking for embeddings
Preserves speaker context and semantic coherence
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


class ChunkStrategy(str, Enum):
    """Chunking strategies"""
    TURN_BASED = "turn_based"          # Chunk by conversation turns
    SLIDING_WINDOW = "sliding_window"   # Fixed size with overlap
    SEMANTIC = "semantic"               # Semantic boundaries (topics)
    SPEAKER_GROUPED = "speaker_grouped" # Group consecutive speaker turns


@dataclass
class Chunk:
    """Conversation chunk for embedding"""
    chunk_id: str
    conversation_id: str
    text: str
    speakers: List[str]
    turn_indices: List[int]
    start_turn: int
    end_turn: int
    metadata: Dict[str, Any]

    def __len__(self) -> int:
        return len(self.text)


class ConversationChunker:
    """
    Intelligent chunking of conversations for vector embeddings
    Optimized for conversational context preservation
    """

    def __init__(
        self,
        strategy: ChunkStrategy = ChunkStrategy.SLIDING_WINDOW,
        chunk_size: int = 500,  # tokens (roughly)
        chunk_overlap: int = 100,
        min_chunk_size: int = 50,
        max_chunk_size: int = 1000
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk_conversation(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk a conversation based on strategy

        Args:
            conversation_id: Conversation ID
            turns: List of conversation turns

        Returns:
            List of chunks ready for embedding
        """
        if self.strategy == ChunkStrategy.TURN_BASED:
            return self._chunk_turn_based(conversation_id, turns)
        elif self.strategy == ChunkStrategy.SLIDING_WINDOW:
            return self._chunk_sliding_window(conversation_id, turns)
        elif self.strategy == ChunkStrategy.SPEAKER_GROUPED:
            return self._chunk_speaker_grouped(conversation_id, turns)
        elif self.strategy == ChunkStrategy.SEMANTIC:
            return self._chunk_semantic(conversation_id, turns)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _chunk_turn_based(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk by individual turns or small groups
        Best for: Q&A, interviews
        """
        chunks = []
        current_turns = []
        current_text = []
        current_length = 0

        for idx, turn in enumerate(turns):
            turn_text = f"{turn['speaker']}: {turn['text']}"
            turn_length = len(turn_text.split())  # Rough token count

            if current_length + turn_length > self.chunk_size and current_turns:
                # Create chunk
                chunk = self._create_chunk(
                    conversation_id=conversation_id,
                    turns=current_turns,
                    text="\n".join(current_text),
                    chunk_idx=len(chunks)
                )
                chunks.append(chunk)

                # Reset with overlap
                if self.chunk_overlap > 0 and current_turns:
                    # Keep last turn for overlap
                    current_turns = current_turns[-1:]
                    current_text = current_text[-1:]
                    current_length = len(current_text[0].split())
                else:
                    current_turns = []
                    current_text = []
                    current_length = 0

            current_turns.append(turn)
            current_text.append(turn_text)
            current_length += turn_length

        # Last chunk
        if current_turns:
            chunk = self._create_chunk(
                conversation_id=conversation_id,
                turns=current_turns,
                text="\n".join(current_text),
                chunk_idx=len(chunks)
            )
            chunks.append(chunk)

        return chunks

    def _chunk_sliding_window(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Sliding window with overlap
        Best for: General conversations, meetings
        """
        chunks = []
        window_turns = []
        window_text = []
        window_length = 0
        start_idx = 0

        for idx, turn in enumerate(turns):
            turn_text = f"{turn['speaker']}: {turn['text']}"
            turn_length = len(turn_text.split())

            window_turns.append(turn)
            window_text.append(turn_text)
            window_length += turn_length

            # Create chunk when size reached
            if window_length >= self.chunk_size:
                chunk = self._create_chunk(
                    conversation_id=conversation_id,
                    turns=window_turns.copy(),
                    text="\n".join(window_text),
                    chunk_idx=len(chunks)
                )
                chunks.append(chunk)

                # Slide window with overlap
                overlap_tokens = 0
                new_window_turns = []
                new_window_text = []

                # Keep turns from end until overlap size reached
                for t, txt in zip(reversed(window_turns), reversed(window_text)):
                    tokens = len(txt.split())
                    if overlap_tokens + tokens <= self.chunk_overlap:
                        new_window_turns.insert(0, t)
                        new_window_text.insert(0, txt)
                        overlap_tokens += tokens
                    else:
                        break

                window_turns = new_window_turns
                window_text = new_window_text
                window_length = overlap_tokens

        # Last chunk
        if window_turns and window_length >= self.min_chunk_size:
            chunk = self._create_chunk(
                conversation_id=conversation_id,
                turns=window_turns,
                text="\n".join(window_text),
                chunk_idx=len(chunks)
            )
            chunks.append(chunk)

        return chunks

    def _chunk_speaker_grouped(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Group consecutive turns from same speaker
        Best for: Monologues, presentations
        """
        chunks = []
        current_speaker = None
        current_turns = []
        current_text = []
        current_length = 0

        for turn in turns:
            speaker = turn['speaker']
            turn_text = f"{speaker}: {turn['text']}"
            turn_length = len(turn_text.split())

            # New speaker or size exceeded
            if (speaker != current_speaker and current_speaker is not None) or \
               (current_length + turn_length > self.chunk_size):

                if current_turns:
                    chunk = self._create_chunk(
                        conversation_id=conversation_id,
                        turns=current_turns,
                        text="\n".join(current_text),
                        chunk_idx=len(chunks)
                    )
                    chunks.append(chunk)

                current_turns = []
                current_text = []
                current_length = 0

            current_speaker = speaker
            current_turns.append(turn)
            current_text.append(turn_text)
            current_length += turn_length

        # Last chunk
        if current_turns:
            chunk = self._create_chunk(
                conversation_id=conversation_id,
                turns=current_turns,
                text="\n".join(current_text),
                chunk_idx=len(chunks)
            )
            chunks.append(chunk)

        return chunks

    def _chunk_semantic(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk by semantic topic boundaries
        Best for: Long discussions, topic-heavy conversations
        """
        # Simple implementation: detect topic changes via questions, transitions
        topic_markers = [
            r'\?$',  # Questions
            r'^(maintenant|alors|donc|ensuite|passons|parlons de)',  # Transitions FR
            r'^(now|so|then|next|let\'s talk about)',  # Transitions EN
        ]

        chunks = []
        current_turns = []
        current_text = []
        current_length = 0

        for idx, turn in enumerate(turns):
            turn_text = f"{turn['speaker']}: {turn['text']}"
            turn_length = len(turn_text.split())

            # Check for topic boundary
            is_boundary = any(re.search(pattern, turn['text'].lower().strip())
                            for pattern in topic_markers)

            if (is_boundary and current_turns and current_length > self.min_chunk_size) or \
               (current_length + turn_length > self.chunk_size):

                chunk = self._create_chunk(
                    conversation_id=conversation_id,
                    turns=current_turns,
                    text="\n".join(current_text),
                    chunk_idx=len(chunks)
                )
                chunks.append(chunk)

                current_turns = []
                current_text = []
                current_length = 0

            current_turns.append(turn)
            current_text.append(turn_text)
            current_length += turn_length

        # Last chunk
        if current_turns:
            chunk = self._create_chunk(
                conversation_id=conversation_id,
                turns=current_turns,
                text="\n".join(current_text),
                chunk_idx=len(chunks)
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]],
        text: str,
        chunk_idx: int
    ) -> Chunk:
        """Create a Chunk object"""
        speakers = list(set(t['speaker'] for t in turns))
        turn_indices = [t.get('turn', idx) for idx, t in enumerate(turns)]

        return Chunk(
            chunk_id=f"{conversation_id}_chunk_{chunk_idx}",
            conversation_id=conversation_id,
            text=text,
            speakers=speakers,
            turn_indices=turn_indices,
            start_turn=turn_indices[0] if turn_indices else 0,
            end_turn=turn_indices[-1] if turn_indices else 0,
            metadata={
                'num_turns': len(turns),
                'num_speakers': len(speakers),
                'chunk_index': chunk_idx,
                'strategy': self.strategy.value
            }
        )

    def estimate_chunks(self, total_turns: int, avg_turn_length: int = 50) -> int:
        """Estimate number of chunks for a conversation"""
        total_tokens = total_turns * avg_turn_length
        tokens_per_chunk = self.chunk_size - (self.chunk_overlap // 2)
        return max(1, total_tokens // tokens_per_chunk)


def smart_chunk_conversation(
    conversation_id: str,
    turns: List[Dict[str, Any]],
    target_embedding_tokens: int = 500
) -> List[Chunk]:
    """
    Smart chunking that adapts to conversation characteristics

    Args:
        conversation_id: ID
        turns: Conversation turns
        target_embedding_tokens: Target tokens per chunk

    Returns:
        Optimized chunks
    """
    # Analyze conversation
    total_turns = len(turns)
    speakers = set(t['speaker'] for t in turns)
    num_speakers = len(speakers)

    # Determine best strategy
    if total_turns <= 10:
        # Short conversation: keep together
        strategy = ChunkStrategy.TURN_BASED
        chunk_size = 1000
    elif num_speakers == 1:
        # Monologue: group by size
        strategy = ChunkStrategy.SLIDING_WINDOW
        chunk_size = target_embedding_tokens
    elif num_speakers == 2:
        # Dialog: speaker-aware
        strategy = ChunkStrategy.SPEAKER_GROUPED
        chunk_size = target_embedding_tokens
    else:
        # Multi-party: semantic or sliding window
        strategy = ChunkStrategy.SEMANTIC
        chunk_size = target_embedding_tokens

    logger.info(
        f"Chunking conversation {conversation_id}: {total_turns} turns, "
        f"{num_speakers} speakers, strategy: {strategy.value}"
    )

    chunker = ConversationChunker(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=100,
        min_chunk_size=50
    )

    return chunker.chunk_conversation(conversation_id, turns)
