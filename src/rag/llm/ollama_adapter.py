"""
Ollama LLM adapter for my-RAG
Lightweight alternative to HuggingFace Transformers

Ollama advantages:
- Lower VRAM usage (~6GB vs ~16GB)
- Faster inference (15-30 tokens/s vs 2-5)
- Simple setup (no quantization config)
- Native streaming support
- REST API compatibility
"""

import time
import logging
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import ollama, provide helpful error if not available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning(
        "Ollama not installed. Install with: pip install ollama\n"
        "Download Ollama from: https://ollama.com/download"
    )


@dataclass
class OllamaConfig:
    """Configuration for Ollama LLM"""
    model: str = "mistral:7b-instruct"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    timeout: int = 60


class OllamaLLM:
    """
    Ollama LLM wrapper compatible with my-RAG chains

    Examples:
        >>> config = OllamaConfig(model="mistral:7b-instruct")
        >>> llm = OllamaLLM(config)
        >>> response = llm.generate("Explain RAG in simple terms")
        >>> print(response)
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "Ollama not installed. Install with: pip install ollama"
            )

        self.config = config or OllamaConfig()

        try:
            self.client = ollama.Client(host=self.config.base_url)
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.config.base_url}. "
                f"Make sure Ollama is running. Error: {e}"
            )

        # Verify model is available
        self._ensure_model_available()

        logger.info(f"OllamaLLM initialized with model: {self.config.model}")

    def _ensure_model_available(self):
        """Check if model is downloaded, pull if not"""
        try:
            response = self.client.list()
            models = response.get('models', [])
            model_names = [m['name'] for m in models]

            if self.config.model not in model_names:
                logger.warning(
                    f"Model {self.config.model} not found locally. "
                    f"Downloading... (this may take a few minutes)"
                )
                self.client.pull(self.config.model)
                logger.info(f"Model {self.config.model} downloaded successfully")
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            raise RuntimeError(
                f"Failed to verify model {self.config.model}. "
                f"Try running: ollama pull {self.config.model}"
            )

    def generate(self,
                 prompt: str,
                 system_prompt: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> str:
        """
        Generate response using Ollama

        Args:
            prompt: User prompt/question
            system_prompt: System instructions (optional)
            max_tokens: Max tokens to generate (overrides config)
            temperature: Sampling temperature (overrides config)

        Returns:
            Generated text response

        Example:
            >>> llm = OllamaLLM()
            >>> response = llm.generate(
            ...     prompt="What is RAG?",
            ...     system_prompt="You are a helpful assistant."
            ... )
        """
        start_time = time.time()

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })

            messages.append({
                'role': 'user',
                'content': prompt
            })

            # Generate with Ollama
            response = self.client.chat(
                model=self.config.model,
                messages=messages,
                options={
                    'temperature': temperature if temperature is not None else self.config.temperature,
                    'top_p': self.config.top_p,
                    'num_predict': max_tokens or self.config.max_tokens
                },
                stream=False
            )

            generated_text = response['message']['content']

            duration = time.time() - start_time
            tokens_generated = len(generated_text.split())  # Rough estimate
            tokens_per_sec = tokens_generated / duration if duration > 0 else 0

            logger.info(
                f"Generated {tokens_generated} tokens in {duration:.2f}s "
                f"({tokens_per_sec:.1f} tokens/s)"
            )

            return generated_text.strip()

        except Exception as e:
            logger.error(f"Error generating response with Ollama: {e}")
            raise

    def generate_stream(self,
                       prompt: str,
                       system_prompt: Optional[str] = None,
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None) -> Generator[str, None, None]:
        """
        Generate response with streaming (yields tokens as generated)

        Args:
            prompt: User prompt
            system_prompt: System instructions (optional)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Yields:
            str: Token chunks as they're generated

        Example:
            >>> llm = OllamaLLM()
            >>> for chunk in llm.generate_stream("Explain RAG"):
            ...     print(chunk, end='', flush=True)
        """
        try:
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

            stream = self.client.chat(
                model=self.config.model,
                messages=messages,
                options={
                    'temperature': temperature if temperature is not None else self.config.temperature,
                    'top_p': self.config.top_p,
                    'num_predict': max_tokens or self.config.max_tokens
                },
                stream=True
            )

            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise

    def embed(self, text: str) -> list:
        """
        Generate embeddings using Ollama's embedding models

        Args:
            text: Text to embed

        Returns:
            List of embedding values

        Note:
            Requires embedding model like 'nomic-embed-text'
            Download with: ollama pull nomic-embed-text
        """
        try:
            response = self.client.embeddings(
                model=self.config.model,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise


class OllamaRAGChain:
    """
    RAG Chain using Ollama instead of HuggingFace
    Drop-in replacement for BaseRAGChain from rag_chains.py

    Example:
        >>> from src.rag.retrieval.hybrid_retriever import ConversationSearchEngine
        >>> search_engine = ConversationSearchEngine(...)
        >>> chain = OllamaRAGChain(search_engine)
        >>> response = chain.process("What projects are we working on?")
    """

    def __init__(self,
                 search_engine,
                 ollama_config: Optional[OllamaConfig] = None):
        """
        Initialize Ollama RAG chain

        Args:
            search_engine: ConversationSearchEngine instance
            ollama_config: Ollama configuration (optional)
        """
        self.search_engine = search_engine
        self.llm = OllamaLLM(ollama_config)

        logger.info("OllamaRAGChain initialized")

    def get_system_prompt(self) -> str:
        """
        Get system prompt for this chain
        Override in subclasses for specialized prompts
        """
        return """Tu es un assistant expert en analyse de conversations professionnelles.
Ton rôle est d'analyser les conversations et d'extraire des insights utiles.

Instructions:
- Réponds en français de manière claire et structurée
- Identifie les points clés, décisions et actions
- Mets en évidence les préoccupations et opportunités
- Propose des suggestions concrètes
- Base-toi uniquement sur les informations fournies dans le contexte
- Si l'information n'est pas dans le contexte, dis-le clairement"""

    def format_context(self, search_results: list) -> str:
        """
        Format search results as context for LLM

        Args:
            search_results: List of SearchResult objects

        Returns:
            Formatted context string
        """
        if not search_results:
            return "Aucune information trouvée."

        context_parts = []

        for i, result in enumerate(search_results[:5]):  # Top 5 results
            chunk = result.chunk
            date = chunk.metadata.get('date', 'Date inconnue')[:10]
            participants = ', '.join(chunk.metadata.get('participants', []))

            context_parts.append(f"""
Conversation {i+1} (Pertinence: {result.relevance_score:.2f}):
Date: {date}
Participants: {participants}
Contenu: {chunk.text}
---""")

        return '\n'.join(context_parts)

    def process(self, query: str, **search_kwargs) -> 'RAGResponse':
        """
        Main RAG pipeline using Ollama

        Args:
            query: User question/query
            **search_kwargs: Additional arguments for search
                - max_results: Number of results to retrieve
                - similarity_threshold: Minimum similarity score
                - date_filter: Date range tuple
                - person_filter: List of person names

        Returns:
            RAGResponse with answer, sources, confidence, etc.

        Example:
            >>> response = chain.process(
            ...     "What did we discuss about project X?",
            ...     max_results=10,
            ...     date_filter=(start_date, end_date)
            ... )
            >>> print(response.answer)
        """
        from ..chains.rag_chains import RAGResponse

        start_time = datetime.now()

        # Step 1: Search for relevant conversations
        logger.info(f"Searching for: {query}")
        search_results = self.search_engine.search_conversations(query, **search_kwargs)
        logger.info(f"Found {len(search_results)} relevant chunks")

        # Step 2: Format context from search results
        context = self.format_context(search_results)

        # Step 3: Build prompt
        prompt = f"""Contexte (conversations pertinentes):
{context}

Question de l'utilisateur: {query}

Réponds en te basant uniquement sur le contexte fourni ci-dessus."""

        # Step 4: Generate response with Ollama
        logger.info("Generating response with Ollama...")
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt()
        )

        # Step 5: Calculate confidence based on search results
        confidence = self._calculate_confidence(search_results)

        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"RAG pipeline completed in {processing_time:.2f}s "
            f"(confidence: {confidence:.2f})"
        )

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=processing_time,
            metadata={
                "query": query,
                "num_sources": len(search_results),
                "chain_type": self.__class__.__name__,
                "llm_backend": "ollama",
                "llm_model": self.llm.config.model
            }
        )

    def _calculate_confidence(self, search_results: list) -> float:
        """
        Calculate confidence score based on search results quality

        Args:
            search_results: List of SearchResult objects

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not search_results:
            return 0.0

        # Weighted average of top results (decreasing weight by position)
        total_score = 0.0
        total_weight = 0.0

        for i, result in enumerate(search_results[:5]):  # Top 5
            weight = 1.0 / (i + 1)  # 1.0, 0.5, 0.33, 0.25, 0.2
            total_score += result.relevance_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0


# Specialized chains using Ollama

class OllamaPersonProfileChain(OllamaRAGChain):
    """Profile generation chain using Ollama"""

    def get_system_prompt(self) -> str:
        return """Tu es un assistant spécialisé dans l'analyse de profils personnels et professionnels.
Ton rôle est de synthétiser les informations sur une personne à partir des conversations.

Instructions:
- Crée un profil détaillé et structuré
- Inclus les informations personnelles (famille, anniversaires, centres d'intérêt)
- Détaille les aspects professionnels (projets, objectifs, défis)
- Identifie le style de communication et les préférences
- Propose des suggestions pour améliorer la relation
- Respecte la confidentialité et reste factuel"""


class OllamaMeetingSuggestionChain(OllamaRAGChain):
    """Meeting preparation chain using Ollama"""

    def get_system_prompt(self) -> str:
        return """Tu es un assistant expert en préparation de réunions et relations professionnelles.
Ton rôle est de proposer des sujets de conversation et points d'attention pour les prochaines interactions.

Instructions:
- Propose 5-7 suggestions concrètes et actionnables
- Inclus des points personnels (anniversaires, famille) et professionnels
- Identifie les sujets à éviter ou les points sensibles
- Suggère des opportunités de collaboration
- Priorise les suggestions par importance
- Donne des exemples de formulations diplomatiques"""


class OllamaProjectAnalysisChain(OllamaRAGChain):
    """Project analysis chain using Ollama"""

    def get_system_prompt(self) -> str:
        return """Tu es un assistant expert en gestion de projet et analyse de discussions.
Ton rôle est d'analyser les conversations liées aux projets et d'extraire des insights stratégiques.

Instructions:
- Identifie l'état d'avancement des projets
- Détecte les blocages et les risques
- Propose des actions correctives
- Identifie les parties prenantes clés
- Analyse les décisions prises et leur impact
- Suggère des améliorations de processus"""
