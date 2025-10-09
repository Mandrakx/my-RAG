"""
Qdrant vector database management
Collection creation, indexing, and search
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue,
    SearchRequest, QueryResponse,
    CollectionInfo, PayloadSchemaType,
    CreateCollection, VectorParams, OptimizersConfigDiff
)
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result from Qdrant"""
    chunk_id: str
    conversation_id: str
    score: float
    text: str
    speakers: List[str]
    turn_range: tuple
    metadata: Dict[str, Any]


class QdrantManager:
    """
    Manage Qdrant collections and operations
    Optimized for conversation embeddings
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None
    ):
        self.client = QdrantClient(url=url, api_key=api_key)
        logger.info(f"Connected to Qdrant at {url}")

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE,
        on_disk: bool = False
    ):
        """
        Create a new collection for embeddings

        Args:
            collection_name: Collection name
            vector_size: Embedding dimension
            distance: Distance metric (COSINE, EUCLID, DOT)
            on_disk: Store vectors on disk (saves VRAM)
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            if any(c.name == collection_name for c in collections):
                logger.info(f"Collection '{collection_name}' already exists")
                return

            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                    on_disk=on_disk
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000,  # Start indexing after 10k points
                    memmap_threshold=20000     # Use memory mapping for >20k points
                )
            )

            # Create payload indexes for faster filtering
            self._create_payload_indexes(collection_name)

            logger.info(f"Created collection '{collection_name}' with {vector_size}d vectors")

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise

    def _create_payload_indexes(self, collection_name: str):
        """Create indexes on frequently queried fields"""
        indexes = [
            ("conversation_id", PayloadSchemaType.KEYWORD),
            ("speakers", PayloadSchemaType.KEYWORD),
            ("turn_range", PayloadSchemaType.INTEGER)
        ]

        for field_name, schema_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=schema_type
                )
                logger.debug(f"Created index on '{field_name}'")
            except Exception as e:
                logger.warning(f"Could not create index on '{field_name}': {e}")

    def upsert_embeddings(
        self,
        collection_name: str,
        embeddings: List[Dict[str, Any]],
        batch_size: int = 100
    ):
        """
        Upsert embeddings to collection

        Args:
            collection_name: Collection name
            embeddings: List of dicts with id, vector, payload
            batch_size: Batch size for upsert
        """
        total = len(embeddings)
        logger.info(f"Upserting {total} embeddings to '{collection_name}'")

        for i in range(0, total, batch_size):
            batch = embeddings[i:i + batch_size]

            points = [
                PointStruct(
                    id=emb['id'],
                    vector=emb['vector'],
                    payload=emb.get('payload', {})
                )
                for emb in batch
            ]

            self.client.upsert(
                collection_name=collection_name,
                points=points
            )

            logger.debug(f"Upserted batch {i//batch_size + 1}/{(total-1)//batch_size + 1}")

        logger.info(f"Successfully upserted {total} embeddings")

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search for similar vectors

        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Max results
            filters: Payload filters (e.g., {'conversation_id': 'abc123'})
            score_threshold: Minimum similarity score

        Returns:
            List of SearchResult
        """
        # Build filter
        search_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    # Multiple values (OR)
                    for v in value:
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=v))
                        )
                else:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )

            if conditions:
                search_filter = Filter(should=conditions)

        # Search
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter,
            score_threshold=score_threshold
        )

        # Convert to SearchResult
        search_results = []
        for result in results:
            search_results.append(
                SearchResult(
                    chunk_id=result.id,
                    conversation_id=result.payload.get('conversation_id'),
                    score=result.score,
                    text=result.payload.get('text', ''),
                    speakers=result.payload.get('speakers', []),
                    turn_range=tuple(result.payload.get('turn_range', [0, 0])),
                    metadata=result.payload
                )
            )

        return search_results

    def delete_conversation(self, collection_name: str, conversation_id: str):
        """Delete all chunks for a conversation"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="conversation_id",
                        match=MatchValue(value=conversation_id)
                    )
                ]
            )
        )
        logger.info(f"Deleted conversation {conversation_id} from {collection_name}")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        info = self.client.get_collection(collection_name)
        return {
            'name': collection_name,
            'vectors_count': info.vectors_count,
            'points_count': info.points_count,
            'segments_count': info.segments_count,
            'status': info.status,
            'optimizer_status': info.optimizer_status,
            'config': {
                'vector_size': info.config.params.vectors.size,
                'distance': info.config.params.vectors.distance.value
            }
        }

    def scroll_collection(
        self,
        collection_name: str,
        limit: int = 100,
        offset: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ):
        """Scroll through collection (for debugging/export)"""
        scroll_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            scroll_filter = Filter(must=conditions)

        results, next_offset = self.client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            scroll_filter=scroll_filter,
            with_payload=True,
            with_vectors=False
        )

        return results, next_offset


class HybridSearch:
    """
    Hybrid search combining dense and sparse retrieval
    """

    def __init__(self, qdrant_manager: QdrantManager):
        self.qdrant = qdrant_manager

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: str,
        limit: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Hybrid search with dense (vector) and sparse (keyword) retrieval

        Args:
            collection_name: Collection name
            query_vector: Dense query vector
            query_text: Query text for keyword search
            limit: Max results
            dense_weight: Weight for dense search
            sparse_weight: Weight for sparse search
            filters: Payload filters

        Returns:
            Combined and reranked results
        """
        # Dense search (vector similarity)
        dense_results = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit * 2,  # Get more for reranking
            filters=filters
        )

        # Sparse search (keyword matching via payload)
        # For now, just use dense search
        # TODO: Implement BM25 sparse search when Qdrant supports it

        # Combine and rerank
        combined = {}
        for result in dense_results:
            score = result.score * dense_weight
            combined[result.chunk_id] = (result, score)

        # Sort by combined score
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [r[0] for r in sorted_results]


def setup_qdrant_collections(
    url: str = "http://localhost:6333",
    api_key: Optional[str] = None
):
    """
    Setup all required Qdrant collections

    Returns:
        QdrantManager instance
    """
    manager = QdrantManager(url=url, api_key=api_key)

    # Create collections with different configurations
    collections_config = [
        {
            'name': 'conversations',
            'vector_size': 1024,  # e5-large-instruct
            'distance': Distance.COSINE,
            'on_disk': False
        },
        {
            'name': 'conversations_openai',
            'vector_size': 1536,  # text-embedding-3-small
            'distance': Distance.COSINE,
            'on_disk': False
        }
    ]

    for config in collections_config:
        try:
            manager.create_collection(**config)
        except Exception as e:
            logger.warning(f"Could not create collection {config['name']}: {e}")

    return manager


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Setup collections
    manager = setup_qdrant_collections()

    # Print collection info
    for collection in ['conversations', 'conversations_openai']:
        try:
            info = manager.get_collection_info(collection)
            print(f"\nCollection: {info['name']}")
            print(f"  Points: {info['points_count']}")
            print(f"  Vectors: {info['vectors_count']}")
            print(f"  Vector size: {info['config']['vector_size']}")
            print(f"  Distance: {info['config']['distance']}")
        except Exception as e:
            print(f"Collection {collection} not found: {e}")
