"""
Hybrid retrieval system combining dense and sparse retrieval with reranking
Optimized for conversation analysis with multi-modal queries
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from sentence_transformers import CrossEncoder
from transformers import AutoTokenizer, AutoModel

from ..embeddings.hybrid_embedder import HybridEmbedder, DocumentChunk, FAISSVectorStore
from ..models.conversation import GPSCoordinate, ConversationMetadata
from ..config.gpu_config import model_manager

logger = logging.getLogger(__name__)

@dataclass
class SearchQuery:
    """Represents a search query with multi-modal components"""
    text: str
    gps_filter: Optional[GPSCoordinate] = None
    date_filter: Optional[Tuple[datetime, datetime]] = None
    person_filter: Optional[List[str]] = None
    conversation_type_filter: Optional[str] = None
    max_results: int = 10
    similarity_threshold: float = 0.7
    use_reranking: bool = True

@dataclass
class SearchResult:
    """Search result with relevance score and metadata"""
    chunk: DocumentChunk
    relevance_score: float
    retrieval_score: float
    rerank_score: Optional[float] = None
    explanation: str = ""

class SparseRetriever:
    """
    BM25-style sparse retrieval for keyword matching
    """

    def __init__(self):
        self.term_frequencies: Dict[str, Dict[str, float]] = {}
        self.doc_frequencies: Dict[str, int] = {}
        self.total_docs = 0
        self.chunk_index: Dict[str, DocumentChunk] = {}

    def index_chunks(self, chunks: List[DocumentChunk]):
        """Index chunks for sparse retrieval"""
        for chunk in chunks:
            self.chunk_index[chunk.chunk_id] = chunk
            tokens = self._tokenize(chunk.text.lower())

            # Calculate term frequencies
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1

            # Normalize by document length
            doc_length = len(tokens)
            for token in tf:
                tf[token] = tf[token] / doc_length

            self.term_frequencies[chunk.chunk_id] = tf

            # Update document frequencies
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_frequencies[token] = self.doc_frequencies.get(token, 0) + 1

        self.total_docs = len(chunks)
        logger.info(f"Indexed {self.total_docs} chunks for sparse retrieval")

    def search(self, query: str, k: int = 50) -> List[Tuple[DocumentChunk, float]]:
        """Search using BM25 scoring"""
        query_tokens = self._tokenize(query.lower())
        scores = {}

        for chunk_id, chunk_tf in self.term_frequencies.items():
            score = 0.0

            for token in query_tokens:
                if token in chunk_tf:
                    # BM25 scoring
                    tf = chunk_tf[token]
                    df = self.doc_frequencies.get(token, 0)
                    idf = np.log((self.total_docs - df + 0.5) / (df + 0.5))

                    # BM25 parameters
                    k1, b = 1.5, 0.75
                    score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * len(chunk_tf)))

            if score > 0:
                scores[chunk_id] = score

        # Sort by score
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Return top-k results
        results = []
        for chunk_id, score in sorted_results[:k]:
            chunk = self.chunk_index[chunk_id]
            results.append((chunk, score))

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        import re
        # Remove punctuation and split
        tokens = re.findall(r'\w+', text.lower())
        return [token for token in tokens if len(token) > 2]

class CrossEncoderReranker:
    """
    Cross-encoder for reranking retrieved chunks
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        self.model = model_manager.load_model(
            "reranker",
            lambda: CrossEncoder(model_name),
            "reranker"
        )
        logger.info(f"CrossEncoder reranker loaded: {model_name}")

    def rerank(self,
              query: str,
              chunks: List[DocumentChunk],
              scores: List[float],
              top_k: int = 10) -> List[Tuple[DocumentChunk, float, float]]:
        """
        Rerank chunks using cross-encoder
        Returns: List of (chunk, original_score, rerank_score)
        """
        if not chunks:
            return []

        # Prepare pairs for reranking
        pairs = [(query, chunk.text) for chunk in chunks]

        # Get rerank scores
        rerank_scores = self.model.predict(pairs)

        # Combine chunks with both scores
        results = []
        for i, (chunk, original_score) in enumerate(zip(chunks, scores)):
            rerank_score = float(rerank_scores[i])
            results.append((chunk, original_score, rerank_score))

        # Sort by rerank score
        results.sort(key=lambda x: x[2], reverse=True)

        return results[:top_k]

class HybridRetriever:
    """
    Main hybrid retrieval system combining dense, sparse, and reranking
    """

    def __init__(self,
                 embedder: HybridEmbedder,
                 vector_store: FAISSVectorStore,
                 use_sparse: bool = True,
                 use_reranking: bool = True):

        self.embedder = embedder
        self.vector_store = vector_store
        self.use_sparse = use_sparse
        self.use_reranking = use_reranking

        # Initialize sparse retriever
        if use_sparse:
            self.sparse_retriever = SparseRetriever()

        # Initialize reranker
        if use_reranking:
            self.reranker = CrossEncoderReranker()

        logger.info(f"HybridRetriever initialized: sparse={use_sparse}, reranking={use_reranking}")

    def index_chunks(self, chunks: List[DocumentChunk]):
        """Index chunks in both dense and sparse retrievers"""
        # Index in sparse retriever
        if self.use_sparse:
            self.sparse_retriever.index_chunks(chunks)

        # Dense indexing is handled by the vector store
        logger.info(f"Indexed {len(chunks)} chunks in hybrid retriever")

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Main search method combining multiple retrieval strategies
        """
        results = []

        # Dense retrieval
        dense_results = self._dense_search(query)

        # Sparse retrieval
        sparse_results = []
        if self.use_sparse:
            sparse_results = self._sparse_search(query)

        # Merge results
        merged_results = self._merge_results(dense_results, sparse_results)

        # Apply filters
        filtered_results = self._apply_filters(merged_results, query)

        # Reranking
        if self.use_reranking and query.use_reranking:
            final_results = self._rerank_results(query.text, filtered_results)
        else:
            final_results = filtered_results

        # Convert to SearchResult objects
        search_results = []
        for i, (chunk, retrieval_score, rerank_score) in enumerate(final_results[:query.max_results]):
            relevance_score = rerank_score if rerank_score is not None else retrieval_score

            if relevance_score >= query.similarity_threshold:
                result = SearchResult(
                    chunk=chunk,
                    relevance_score=relevance_score,
                    retrieval_score=retrieval_score,
                    rerank_score=rerank_score,
                    explanation=self._generate_explanation(chunk, query, relevance_score)
                )
                search_results.append(result)

        return search_results

    def _dense_search(self, query: SearchQuery) -> List[Tuple[DocumentChunk, float]]:
        """Dense retrieval using embeddings"""
        # Create query embedding
        query_embedding = self.embedder.encode_hybrid(
            texts=[query.text],
            gps_coords=[query.gps_filter] if query.gps_filter else None,
            timestamps=[datetime.now()]  # Use current time as default
        )

        # Search in vector store
        chunks, scores = self.vector_store.search(
            query_embedding,
            k=min(100, query.max_results * 5)  # Retrieve more for reranking
        )

        return list(zip(chunks, scores))

    def _sparse_search(self, query: SearchQuery) -> List[Tuple[DocumentChunk, float]]:
        """Sparse retrieval using BM25"""
        if not hasattr(self, 'sparse_retriever'):
            return []

        return self.sparse_retriever.search(
            query.text,
            k=min(50, query.max_results * 3)
        )

    def _merge_results(self,
                      dense_results: List[Tuple[DocumentChunk, float]],
                      sparse_results: List[Tuple[DocumentChunk, float]]) -> List[Tuple[DocumentChunk, float]]:
        """
        Merge dense and sparse results using reciprocal rank fusion
        """
        # Convert to dictionaries for easier merging
        dense_dict = {chunk.chunk_id: (chunk, score) for chunk, score in dense_results}
        sparse_dict = {chunk.chunk_id: (chunk, score) for chunk, score in sparse_results}

        # Reciprocal rank fusion
        merged_scores = {}
        k = 60  # RRF parameter

        # Add dense scores
        for i, (chunk_id, (chunk, score)) in enumerate(dense_dict.items()):
            merged_scores[chunk_id] = (chunk, 1.0 / (k + i + 1))

        # Add sparse scores
        for i, (chunk_id, (chunk, score)) in enumerate(sparse_dict.items()):
            if chunk_id in merged_scores:
                existing_chunk, existing_score = merged_scores[chunk_id]
                merged_scores[chunk_id] = (existing_chunk, existing_score + 1.0 / (k + i + 1))
            else:
                merged_scores[chunk_id] = (chunk, 1.0 / (k + i + 1))

        # Sort by merged score
        sorted_results = sorted(
            merged_scores.values(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_results

    def _apply_filters(self,
                      results: List[Tuple[DocumentChunk, float]],
                      query: SearchQuery) -> List[Tuple[DocumentChunk, float]]:
        """Apply query filters to results"""
        filtered_results = []

        for chunk, score in results:
            # Date filter
            if query.date_filter:
                start_date, end_date = query.date_filter
                if chunk.timestamp and not (start_date <= chunk.timestamp <= end_date):
                    continue

            # GPS proximity filter
            if query.gps_filter and chunk.gps:
                distance = self._calculate_distance(query.gps_filter, chunk.gps)
                if distance > 50.0:  # 50km radius
                    continue

            # Person filter
            if query.person_filter:
                chunk_participants = chunk.metadata.get('participants', [])
                if not any(person in chunk_participants for person in query.person_filter):
                    continue

            # Conversation type filter
            if query.conversation_type_filter:
                chunk_type = chunk.metadata.get('conversation_type')
                if chunk_type != query.conversation_type_filter:
                    continue

            filtered_results.append((chunk, score))

        return filtered_results

    def _rerank_results(self,
                       query: str,
                       results: List[Tuple[DocumentChunk, float]]) -> List[Tuple[DocumentChunk, float, Optional[float]]]:
        """Rerank results using cross-encoder"""
        if not results:
            return []

        chunks = [chunk for chunk, _ in results]
        scores = [score for _, score in results]

        reranked = self.reranker.rerank(query, chunks, scores)

        # Convert to expected format
        final_results = []
        for chunk, original_score, rerank_score in reranked:
            final_results.append((chunk, original_score, rerank_score))

        return final_results

    def _calculate_distance(self, gps1: GPSCoordinate, gps2: GPSCoordinate) -> float:
        """Calculate distance between two GPS coordinates (Haversine formula)"""
        import math

        R = 6371  # Earth's radius in kilometers

        lat1, lon1 = math.radians(gps1.latitude), math.radians(gps1.longitude)
        lat2, lon2 = math.radians(gps2.latitude), math.radians(gps2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _generate_explanation(self,
                            chunk: DocumentChunk,
                            query: SearchQuery,
                            relevance_score: float) -> str:
        """Generate explanation for why this chunk was retrieved"""
        explanations = []

        if relevance_score > 0.9:
            explanations.append("Très pertinent")
        elif relevance_score > 0.7:
            explanations.append("Pertinent")
        else:
            explanations.append("Potentiellement pertinent")

        # Add context about the conversation
        if chunk.metadata.get('participants'):
            participants = ', '.join(chunk.metadata['participants'])
            explanations.append(f"Participants: {participants}")

        if chunk.metadata.get('date'):
            date_str = chunk.metadata['date'][:10]  # YYYY-MM-DD
            explanations.append(f"Date: {date_str}")

        return " | ".join(explanations)

    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        stats = {
            "vector_store_stats": self.vector_store.get_stats(),
            "use_sparse": self.use_sparse,
            "use_reranking": self.use_reranking
        }

        if self.use_sparse:
            stats["sparse_stats"] = {
                "total_docs": self.sparse_retriever.total_docs,
                "vocabulary_size": len(self.sparse_retriever.doc_frequencies)
            }

        return stats

class ConversationSearchEngine:
    """
    High-level search engine for conversation analysis
    """

    def __init__(self,
                 embedder: HybridEmbedder,
                 vector_store: FAISSVectorStore):

        self.embedder = embedder
        self.vector_store = vector_store
        self.retriever = HybridRetriever(embedder, vector_store)

    def index_conversation(self, conversation_text: str, metadata: ConversationMetadata) -> List[DocumentChunk]:
        """Index a complete conversation"""
        from ..embeddings.hybrid_embedder import SemanticChunker

        # Chunk the conversation
        chunker = SemanticChunker()
        chunks = chunker.chunk_conversation(conversation_text, metadata.conversation_id, metadata)

        # Generate embeddings
        embeddings = self.embedder.encode_document_chunks(chunks)

        # Add to vector store
        self.vector_store.add_chunks(chunks, embeddings)

        # Add to sparse index
        self.retriever.index_chunks(chunks)

        logger.info(f"Indexed conversation {metadata.conversation_id} with {len(chunks)} chunks")
        return chunks

    def search_conversations(self, query_text: str, **kwargs) -> List[SearchResult]:
        """Search conversations with natural language query"""
        query = SearchQuery(text=query_text, **kwargs)
        return self.retriever.search(query)

    def search_by_person(self, person_name: str, query_text: str = "", **kwargs) -> List[SearchResult]:
        """Search conversations involving a specific person"""
        query = SearchQuery(
            text=query_text or f"conversations with {person_name}",
            person_filter=[person_name],
            **kwargs
        )
        return self.retriever.search(query)

    def search_by_location(self, gps: GPSCoordinate, query_text: str = "", **kwargs) -> List[SearchResult]:
        """Search conversations by location"""
        query = SearchQuery(
            text=query_text or "conversations at this location",
            gps_filter=gps,
            **kwargs
        )
        return self.retriever.search(query)

    def search_by_date_range(self,
                           start_date: datetime,
                           end_date: datetime,
                           query_text: str = "",
                           **kwargs) -> List[SearchResult]:
        """Search conversations within a date range"""
        query = SearchQuery(
            text=query_text or f"conversations between {start_date.date()} and {end_date.date()}",
            date_filter=(start_date, end_date),
            **kwargs
        )
        return self.retriever.search(query)