"""
NLP processing orchestrator
Coordinates chunking, embeddings, NER, and sentiment analysis
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio

from .chunking import smart_chunk_conversation, Chunk
from .embeddings import get_embedding_generator, EmbeddingGenerator
from .ner import EntityExtractor, PersonExtractor
from .sentiment import SentimentAnalyzer, analyze_conversation_mood
from .qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


@dataclass
class NLPProcessingResult:
    """Result of NLP processing"""
    conversation_id: str
    num_chunks: int
    num_embeddings: int
    entities: Dict[str, Any]
    persons: List[Dict[str, Any]]
    sentiment_analysis: Dict[str, Any]
    indexed: bool
    processing_time_ms: int


class NLPProcessor:
    """
    Orchestrates all NLP processing steps
    Optimized for GPU batching and parallel execution
    """

    def __init__(
        self,
        embedding_provider: str = "local_gpu",
        embedding_model: str = "intfloat/multilingual-e5-large-instruct",
        ner_model: str = "camembert/camembert-ner",
        sentiment_model: str = "nlptown/bert-base-multilingual-uncased-sentiment",
        device: str = "cuda",
        qdrant_url: str = "http://localhost:6333",
        qdrant_collection: str = "conversations"
    ):
        self.device = device
        self.qdrant_collection = qdrant_collection

        # Initialize components
        logger.info("Initializing NLP Processor...")

        self.embedding_generator = get_embedding_generator(
            provider=embedding_provider,
            model_name=embedding_model,
            device=device
        )

        self.entity_extractor = EntityExtractor(
            model_name=ner_model,
            device=device
        )

        self.person_extractor = PersonExtractor(self.entity_extractor)

        self.sentiment_analyzer = SentimentAnalyzer(
            model_name=sentiment_model,
            device=device
        )

        self.qdrant_manager = QdrantManager(url=qdrant_url)

        logger.info("NLP Processor initialized successfully")

    async def process_conversation(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> NLPProcessingResult:
        """
        Complete NLP processing pipeline

        Args:
            conversation_id: Conversation ID
            turns: List of conversation turns
            metadata: Optional conversation metadata

        Returns:
            NLPProcessingResult with all processed data
        """
        import time
        start_time = time.time()

        logger.info(f"Processing conversation {conversation_id} with {len(turns)} turns")

        # Step 1: Chunking
        logger.info(f"[{conversation_id}] Step 1/5: Chunking...")
        chunks = smart_chunk_conversation(
            conversation_id=conversation_id,
            turns=turns,
            target_embedding_tokens=500
        )
        logger.info(f"[{conversation_id}] Created {len(chunks)} chunks")

        # Step 2: Generate embeddings
        logger.info(f"[{conversation_id}] Step 2/5: Generating embeddings...")
        embedding_results = self.embedding_generator.embed_chunks(chunks, show_progress=True)
        logger.info(f"[{conversation_id}] Generated {len(embedding_results)} embeddings")

        # Step 3: Index in Qdrant
        logger.info(f"[{conversation_id}] Step 3/5: Indexing in Qdrant...")
        await self._index_embeddings(
            conversation_id=conversation_id,
            chunks=chunks,
            embedding_results=embedding_results,
            metadata=metadata
        )

        # Step 4 & 5: NER and Sentiment in parallel
        logger.info(f"[{conversation_id}] Step 4-5/5: Parallel NER and Sentiment analysis...")

        # Run NER and Sentiment in parallel
        ner_task = asyncio.create_task(self._extract_entities(turns))
        sentiment_task = asyncio.create_task(self._analyze_sentiment(turns))

        entities_data, sentiment_data = await asyncio.gather(ner_task, sentiment_task)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{conversation_id}] Processing complete in {processing_time_ms}ms: "
            f"{len(chunks)} chunks, {len(entities_data['persons'])} persons, "
            f"{sentiment_data['stats']['avg_stars']:.1f} avg sentiment"
        )

        return NLPProcessingResult(
            conversation_id=conversation_id,
            num_chunks=len(chunks),
            num_embeddings=len(embedding_results),
            entities=entities_data['entities'],
            persons=entities_data['persons'],
            sentiment_analysis=sentiment_data,
            indexed=True,
            processing_time_ms=processing_time_ms
        )

    async def _index_embeddings(
        self,
        conversation_id: str,
        chunks: List[Chunk],
        embedding_results: List,
        metadata: Optional[Dict[str, Any]]
    ):
        """Index embeddings in Qdrant"""
        embeddings_data = []

        for chunk, emb_result in zip(chunks, embedding_results):
            embeddings_data.append({
                'id': chunk.chunk_id,
                'vector': emb_result.embedding,
                'payload': {
                    'chunk_id': chunk.chunk_id,
                    'conversation_id': conversation_id,
                    'text': chunk.text,
                    'speakers': chunk.speakers,
                    'turn_range': [chunk.start_turn, chunk.end_turn],
                    'num_turns': len(chunk.turn_indices),
                    'chunk_index': chunk.metadata.get('chunk_index'),
                    **(metadata or {})
                }
            })

        self.qdrant_manager.upsert_embeddings(
            collection_name=self.qdrant_collection,
            embeddings=embeddings_data
        )

    async def _extract_entities(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract entities and persons"""
        # Extract all entities
        turn_entities = self.entity_extractor.extract_from_conversation(turns)

        # Aggregate entities
        aggregated_entities = self.entity_extractor.aggregate_entities(turn_entities)

        # Extract persons
        persons = self.person_extractor.extract_persons(turns)

        return {
            'entities': aggregated_entities,
            'persons': persons,
            'turn_entities': {k: [e.__dict__ for e in v] for k, v in turn_entities.items()}
        }

    async def _analyze_sentiment(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment"""
        return analyze_conversation_mood(turns, self.sentiment_analyzer)

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by semantic similarity

        Args:
            query: Search query
            limit: Max results
            filters: Optional filters (e.g., conversation_id, speakers)
            score_threshold: Minimum similarity score

        Returns:
            List of search results with chunks and metadata
        """
        # Generate query embedding
        query_vector = self.embedding_generator.embed_query(query)

        # Search in Qdrant
        results = self.qdrant_manager.search(
            collection_name=self.qdrant_collection,
            query_vector=query_vector,
            limit=limit,
            filters=filters,
            score_threshold=score_threshold
        )

        return [
            {
                'chunk_id': r.chunk_id,
                'conversation_id': r.conversation_id,
                'score': r.score,
                'text': r.text,
                'speakers': r.speakers,
                'turn_range': r.turn_range,
                'metadata': r.metadata
            }
            for r in results
        ]


class NLPProcessorFactory:
    """Factory to create NLP processor with different configurations"""

    @staticmethod
    def create_local_gpu_processor(
        device: str = "cuda",
        qdrant_url: str = "http://localhost:6333"
    ) -> NLPProcessor:
        """Create processor with local GPU models"""
        return NLPProcessor(
            embedding_provider="local_gpu",
            embedding_model="intfloat/multilingual-e5-large-instruct",
            ner_model="camembert/camembert-ner",
            sentiment_model="nlptown/bert-base-multilingual-uncased-sentiment",
            device=device,
            qdrant_url=qdrant_url
        )

    @staticmethod
    def create_openai_processor(
        qdrant_url: str = "http://localhost:6333"
    ) -> NLPProcessor:
        """Create processor with OpenAI embeddings"""
        return NLPProcessor(
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            ner_model="camembert/camembert-ner",
            sentiment_model="nlptown/bert-base-multilingual-uncased-sentiment",
            device="cuda",  # NER/sentiment still on GPU
            qdrant_url=qdrant_url,
            qdrant_collection="conversations_openai"
        )

    @staticmethod
    def create_lightweight_processor(
        device: str = "cpu",
        qdrant_url: str = "http://localhost:6333"
    ) -> NLPProcessor:
        """Create lightweight processor for CPU-only"""
        return NLPProcessor(
            embedding_provider="sentence_transformers",
            embedding_model="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            ner_model="camembert/camembert-ner",
            sentiment_model="nlptown/bert-base-multilingual-uncased-sentiment",
            device=device,
            qdrant_url=qdrant_url
        )


if __name__ == "__main__":
    # Test NLP processor
    logging.basicConfig(level=logging.INFO)

    async def test():
        processor = NLPProcessorFactory.create_local_gpu_processor()

        test_turns = [
            {"turn": 0, "speaker": "Alice", "text": "Bonjour Jean, comment vas-tu?"},
            {"turn": 1, "speaker": "Jean", "text": "Très bien merci! Je travaille chez Google maintenant."},
            {"turn": 2, "speaker": "Alice", "text": "C'est génial! Tu es basé à Paris?"},
            {"turn": 3, "speaker": "Jean", "text": "Oui, dans le bureau du 9ème arrondissement."}
        ]

        result = await processor.process_conversation(
            conversation_id="test-123",
            turns=test_turns
        )

        print(f"\nProcessing Result:")
        print(f"  Chunks: {result.num_chunks}")
        print(f"  Embeddings: {result.num_embeddings}")
        print(f"  Persons: {len(result.persons)}")
        print(f"  Entities: {result.entities}")
        print(f"  Avg Sentiment: {result.sentiment_analysis['stats']['avg_stars']:.1f} stars")
        print(f"  Time: {result.processing_time_ms}ms")

    asyncio.run(test())
