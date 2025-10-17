"""
LM Studio adapter for my-RAG
Alternative to Ollama with GUI interface

LM Studio advantages:
- GUI for model management
- OpenAI-compatible API
- Model marketplace
- Real-time monitoring
- Easy model switching
"""

import requests
import time
import logging
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LMStudioConfig:
    """Configuration for LM Studio LLM"""
    base_url: str = "http://localhost:1234/v1"
    model: str = "local-model"  # LM Studio uses loaded model
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    timeout: int = 60


class LMStudioLLM:
    """
    LM Studio LLM wrapper compatible with my-RAG chains
    Uses OpenAI-compatible API

    Example:
        >>> config = LMStudioConfig()
        >>> llm = LMStudioLLM(config)
        >>> response = llm.generate("Explain RAG")
        >>> print(response)
    """

    def __init__(self, config: Optional[LMStudioConfig] = None):
        self.config = config or LMStudioConfig()

        # Verify LM Studio is running
        self._verify_connection()

        logger.info(f"LMStudioLLM initialized at {self.config.base_url}")

    def _verify_connection(self):
        """Check if LM Studio server is accessible"""
        try:
            response = requests.get(
                f"{self.config.base_url}/models",
                timeout=5
            )
            response.raise_for_status()

            models = response.json()
            logger.info(f"LM Studio connected. Available models: {models}")

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to LM Studio at {self.config.base_url}. "
                f"Make sure LM Studio is running and a model is loaded."
            )
        except Exception as e:
            logger.warning(f"Error verifying LM Studio connection: {e}")

    def generate(self,
                 prompt: str,
                 system_prompt: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> str:
        """
        Generate response using LM Studio (OpenAI-compatible API)

        Args:
            prompt: User prompt
            system_prompt: System instructions
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        start_time = time.time()

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Call LM Studio API (OpenAI-compatible)
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else self.config.temperature,
                    "top_p": self.config.top_p,
                    "max_tokens": max_tokens or self.config.max_tokens,
                    "stream": False
                },
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            generated_text = result['choices'][0]['message']['content']

            duration = time.time() - start_time
            logger.info(f"Generated response in {duration:.2f}s")

            return generated_text.strip()

        except requests.exceptions.Timeout:
            raise TimeoutError(f"LM Studio request timed out after {self.config.timeout}s")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling LM Studio API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def generate_stream(self,
                       prompt: str,
                       system_prompt: Optional[str] = None,
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None) -> Generator[str, None, None]:
        """
        Generate response with streaming

        Yields:
            str: Token chunks as generated
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else self.config.temperature,
                    "top_p": self.config.top_p,
                    "max_tokens": max_tokens or self.config.max_tokens,
                    "stream": True
                },
                stream=True,
                timeout=self.config.timeout
            )

            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix

                        if data_str.strip() == '[DONE]':
                            break

                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data['choices'][0]['delta']

                            if 'content' in delta:
                                yield delta['content']
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise


class LMStudioRAGChain:
    """
    RAG Chain using LM Studio
    Drop-in replacement for BaseRAGChain

    Example:
        >>> from src.rag.retrieval.hybrid_retriever import ConversationSearchEngine
        >>> search_engine = ConversationSearchEngine(...)
        >>> chain = LMStudioRAGChain(search_engine)
        >>> response = chain.process("What are we working on?")
    """

    def __init__(self,
                 search_engine,
                 lmstudio_config: Optional[LMStudioConfig] = None):
        self.search_engine = search_engine
        self.llm = LMStudioLLM(lmstudio_config)

        logger.info("LMStudioRAGChain initialized")

    def get_system_prompt(self) -> str:
        """System prompt for conversation analysis"""
        return """Tu es un assistant expert en analyse de conversations professionnelles.
Ton rôle est d'analyser les conversations et d'extraire des insights utiles.

Instructions:
- Réponds en français de manière claire et structurée
- Identifie les points clés, décisions et actions
- Mets en évidence les préoccupations et opportunités
- Propose des suggestions concrètes
- Base-toi uniquement sur les informations fournies dans le contexte"""

    def format_context(self, search_results: list) -> str:
        """Format search results as context"""
        if not search_results:
            return "Aucune information trouvée."

        context_parts = []
        for i, result in enumerate(search_results[:5]):
            chunk = result.chunk
            context_parts.append(f"""
Conversation {i+1} (Pertinence: {result.relevance_score:.2f}):
Date: {chunk.metadata.get('date', 'N/A')[:10]}
Participants: {', '.join(chunk.metadata.get('participants', []))}
Contenu: {chunk.text}
---""")

        return '\n'.join(context_parts)

    def process(self, query: str, **search_kwargs):
        """Main RAG pipeline using LM Studio"""
        from ..chains.rag_chains import RAGResponse

        start_time = datetime.now()

        # Search
        search_results = self.search_engine.search_conversations(query, **search_kwargs)

        # Format context
        context = self.format_context(search_results)

        # Build prompt
        prompt = f"""Contexte:
{context}

Question: {query}"""

        # Generate with LM Studio
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt()
        )

        # Calculate confidence
        confidence = self._calculate_confidence(search_results)

        processing_time = (datetime.now() - start_time).total_seconds()

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=processing_time,
            metadata={
                "query": query,
                "num_sources": len(search_results),
                "chain_type": self.__class__.__name__,
                "llm_backend": "lmstudio"
            }
        )

    def _calculate_confidence(self, search_results: list) -> float:
        """Calculate confidence score"""
        if not search_results:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for i, result in enumerate(search_results[:5]):
            weight = 1.0 / (i + 1)
            total_score += result.relevance_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0
