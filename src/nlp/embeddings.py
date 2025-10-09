"""
Embedding generation for conversation chunks
Supports local (GPU) and API-based embeddings
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import numpy as np
from enum import Enum
import torch
from transformers import AutoTokenizer, AutoModel
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Embedding providers"""
    LOCAL_GPU = "local_gpu"          # Local transformer model (RTX 3090)
    OPENAI = "openai"                 # OpenAI API
    SENTENCE_TRANSFORMERS = "sentence_transformers"  # Sentence-transformers library


@dataclass
class EmbeddingResult:
    """Embedding result for a chunk"""
    chunk_id: str
    embedding: List[float]
    model: str
    dimensions: int
    metadata: Dict[str, Any] = None


class EmbeddingGenerator:
    """
    Generate embeddings for conversation chunks
    Supports multiple providers and batching
    """

    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.LOCAL_GPU,
        model_name: str = "intfloat/multilingual-e5-large-instruct",
        device: str = "cuda",
        batch_size: int = 32,
        dimensions: int = 1024
    ):
        self.provider = provider
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.batch_size = batch_size
        self.dimensions = dimensions

        # Load model based on provider
        self.model = None
        self.tokenizer = None

        if self.provider == EmbeddingProvider.LOCAL_GPU:
            self._load_local_model()
        elif self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            self._load_sentence_transformer()

        logger.info(f"Initialized EmbeddingGenerator: {provider}, model: {model_name}, device: {self.device}")

    def _load_local_model(self):
        """Load transformer model locally"""
        logger.info(f"Loading model {self.model_name} on {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        self.model.to(self.device)
        self.model.eval()  # Inference mode

        logger.info(f"Model loaded successfully on {self.device}")

    def _load_sentence_transformer(self):
        """Load sentence-transformers model"""
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading sentence-transformer: {self.model_name}")
        self.model = SentenceTransformer(self.model_name, device=self.device)

    def embed_chunks(
        self,
        chunks: List,
        show_progress: bool = False
    ) -> List[EmbeddingResult]:
        """
        Embed multiple chunks in batches

        Args:
            chunks: List of Chunk objects
            show_progress: Show progress bar

        Returns:
            List of EmbeddingResult
        """
        results = []

        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_texts = [chunk.text for chunk in batch]

            # Generate embeddings
            if self.provider == EmbeddingProvider.OPENAI:
                embeddings = self._embed_openai(batch_texts)
            elif self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
                embeddings = self._embed_sentence_transformers(batch_texts)
            else:  # LOCAL_GPU
                embeddings = self._embed_local(batch_texts)

            # Create results
            for chunk, embedding in zip(batch, embeddings):
                result = EmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    embedding=embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
                    model=self.model_name,
                    dimensions=len(embedding),
                    metadata={
                        'conversation_id': chunk.conversation_id,
                        'speakers': chunk.speakers,
                        'turn_range': (chunk.start_turn, chunk.end_turn)
                    }
                )
                results.append(result)

            if show_progress:
                logger.info(f"Embedded batch {i//self.batch_size + 1}/{(len(chunks)-1)//self.batch_size + 1}")

        return results

    def _embed_local(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using local model"""
        # Add instruction prefix for E5 models
        if "e5" in self.model_name.lower():
            texts = [f"passage: {text}" for text in texts]

        # Tokenize
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)

            # Use [CLS] token embedding or mean pooling
            if hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
                embeddings = outputs.pooler_output
            else:
                # Mean pooling
                token_embeddings = outputs.last_hidden_state
                attention_mask = inputs['attention_mask']
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
                    input_mask_expanded.sum(1), min=1e-9
                )

            # Normalize embeddings
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy()

    def _embed_sentence_transformers(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using sentence-transformers"""
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        import openai

        response = openai.embeddings.create(
            model=self.model_name or "text-embedding-3-small",
            input=texts
        )

        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query for search

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        if self.provider == EmbeddingProvider.OPENAI:
            embeddings = self._embed_openai([query])
            return embeddings[0]
        elif self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            embedding = self.model.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embedding.tolist()
        else:  # LOCAL_GPU
            # Add query prefix for E5 models
            if "e5" in self.model_name.lower():
                query = f"query: {query}"

            embeddings = self._embed_local([query])
            return embeddings[0].tolist()

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'provider': self.provider.value,
            'model_name': self.model_name,
            'dimensions': self.dimensions,
            'device': self.device,
            'batch_size': self.batch_size
        }


class EmbeddingPipeline:
    """
    Complete embedding pipeline from conversation to indexed vectors
    """

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        qdrant_client = None
    ):
        self.embedding_generator = embedding_generator
        self.qdrant_client = qdrant_client

    async def process_conversation(
        self,
        conversation_id: str,
        chunks: List,
        collection_name: str = "conversations"
    ) -> Dict[str, Any]:
        """
        Process conversation: chunk → embed → index

        Args:
            conversation_id: Conversation ID
            chunks: List of Chunk objects
            collection_name: Qdrant collection name

        Returns:
            Processing results with statistics
        """
        logger.info(f"Processing conversation {conversation_id}: {len(chunks)} chunks")

        # Generate embeddings
        embedding_results = self.embedding_generator.embed_chunks(chunks, show_progress=True)

        # Index in Qdrant (if client available)
        if self.qdrant_client:
            await self._index_embeddings(
                collection_name=collection_name,
                embedding_results=embedding_results
            )

        return {
            'conversation_id': conversation_id,
            'num_chunks': len(chunks),
            'num_embeddings': len(embedding_results),
            'model': self.embedding_generator.model_name,
            'dimensions': self.embedding_generator.dimensions,
            'indexed': self.qdrant_client is not None
        }

    async def _index_embeddings(
        self,
        collection_name: str,
        embedding_results: List[EmbeddingResult]
    ):
        """Index embeddings in Qdrant"""
        from qdrant_client.models import PointStruct

        points = []
        for result in embedding_results:
            point = PointStruct(
                id=result.chunk_id,
                vector=result.embedding,
                payload={
                    'chunk_id': result.chunk_id,
                    'conversation_id': result.metadata.get('conversation_id'),
                    'speakers': result.metadata.get('speakers'),
                    'turn_range': result.metadata.get('turn_range'),
                    'model': result.model
                }
            )
            points.append(point)

        # Upsert to Qdrant
        self.qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )

        logger.info(f"Indexed {len(points)} embeddings in collection '{collection_name}'")


def get_embedding_generator(
    provider: str = "local_gpu",
    model_name: Optional[str] = None,
    device: str = "cuda"
) -> EmbeddingGenerator:
    """
    Factory function to get embedding generator

    Args:
        provider: Provider type (local_gpu, openai, sentence_transformers)
        model_name: Model name (defaults per provider)
        device: Device (cuda/cpu)

    Returns:
        Configured EmbeddingGenerator
    """
    provider_enum = EmbeddingProvider(provider)

    # Default models per provider
    if model_name is None:
        if provider_enum == EmbeddingProvider.LOCAL_GPU:
            model_name = "intfloat/multilingual-e5-large-instruct"
        elif provider_enum == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        elif provider_enum == EmbeddingProvider.OPENAI:
            model_name = "text-embedding-3-small"

    # Dimensions per model
    dimensions_map = {
        "intfloat/multilingual-e5-large-instruct": 1024,
        "intfloat/multilingual-e5-base": 768,
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": 768,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072
    }

    dimensions = dimensions_map.get(model_name, 768)

    return EmbeddingGenerator(
        provider=provider_enum,
        model_name=model_name,
        device=device,
        dimensions=dimensions
    )
