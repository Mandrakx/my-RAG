"""
Specialized RAG chains for different conversation analysis tasks
Each chain is optimized for specific use cases with custom prompts and logic
"""

import torch
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import logging
from abc import ABC, abstractmethod

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from ..retrieval.hybrid_retriever import ConversationSearchEngine, SearchResult
from ..models.conversation import PersonProfile, MeetingSuggestion, ConversationAnalysis
from ..config.gpu_config import model_manager

logger = logging.getLogger(__name__)

@dataclass
class RAGResponse:
    """Response from a RAG chain"""
    answer: str
    sources: List[SearchResult]
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]

class BaseRAGChain(ABC):
    """Base class for RAG chains"""

    def __init__(self,
                 search_engine: ConversationSearchEngine,
                 llm_model_name: str = "mistralai/Mistral-7B-Instruct-v0.2"):

        self.search_engine = search_engine
        self.llm_model_name = llm_model_name

        # Load LLM with 4-bit quantization for RTX 3090
        self.tokenizer, self.llm = self._load_llm()

    def _load_llm(self):
        """Load quantized LLM for GPU inference"""
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )

        tokenizer = AutoTokenizer.from_pretrained(self.llm_model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        llm = model_manager.load_model(
            "llm",
            lambda: AutoModelForCausalLM.from_pretrained(
                self.llm_model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True
            ),
            "llm"
        )

        return tokenizer, llm

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this chain"""
        pass

    @abstractmethod
    def format_context(self, search_results: List[SearchResult]) -> str:
        """Format search results as context"""
        pass

    def generate_response(self,
                         user_query: str,
                         context: str,
                         max_new_tokens: int = 512) -> str:
        """Generate response using LLM"""

        # Create prompt
        system_prompt = self.get_system_prompt()
        prompt = f"""<s>[INST] {system_prompt}

Context:
{context}

Question: {user_query} [/INST]"""

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(self.llm.device)

        # Generate
        with torch.no_grad():
            outputs = self.llm.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode response
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )

        return response.strip()

    def process(self, query: str, **search_kwargs) -> RAGResponse:
        """Main processing pipeline"""
        start_time = datetime.now()

        # Search for relevant information
        search_results = self.search_engine.search_conversations(query, **search_kwargs)

        # Format context
        context = self.format_context(search_results)

        # Generate response
        answer = self.generate_response(query, context)

        # Calculate confidence based on search results
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
                "chain_type": self.__class__.__name__
            }
        )

    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence score based on search results"""
        if not search_results:
            return 0.0

        # Average relevance score weighted by position
        total_score = 0.0
        total_weight = 0.0

        for i, result in enumerate(search_results[:5]):  # Top 5 results
            weight = 1.0 / (i + 1)  # Decreasing weight
            total_score += result.relevance_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

class ConversationAnalysisChain(BaseRAGChain):
    """Chain for analyzing conversations and extracting insights"""

    def get_system_prompt(self) -> str:
        return """Tu es un assistant expert en analyse de conversations professionnelles.
Ton rôle est d'analyser les conversations et d'extraire des insights utiles.

Instructions:
- Réponds en français de manière claire et structurée
- Identifie les points clés, décisions et actions
- Mets en évidence les préoccupations et opportunités
- Propose des suggestions concrètes
- Base-toi uniquement sur les informations fournies dans le contexte"""

    def format_context(self, search_results: List[SearchResult]) -> str:
        context_parts = []

        for i, result in enumerate(search_results[:5]):
            chunk = result.chunk
            context_parts.append(f"""
Conversation {i+1} (Score: {result.relevance_score:.2f}):
Date: {chunk.metadata.get('date', 'Non spécifiée')[:10]}
Participants: {', '.join(chunk.metadata.get('participants', []))}
Contenu: {chunk.text}
---""")

        return '\n'.join(context_parts)

class PersonProfileChain(BaseRAGChain):
    """Chain for generating person profiles and insights"""

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

    def format_context(self, search_results: List[SearchResult]) -> str:
        context_parts = []

        for result in search_results:
            chunk = result.chunk
            context_parts.append(f"""
Date: {chunk.metadata.get('date', '')[:10]}
Conversation: {chunk.text}
""")

        return '\n'.join(context_parts)

    def generate_profile_summary(self, person_name: str) -> RAGResponse:
        """Generate a comprehensive profile summary for a person"""
        query = f"Informations sur {person_name} - profil personnel et professionnel"

        # Search for conversations involving this person
        search_results = self.search_engine.search_by_person(
            person_name,
            query_text=query,
            max_results=20
        )

        if not search_results:
            return RAGResponse(
                answer=f"Aucune information trouvée sur {person_name}",
                sources=[],
                confidence=0.0,
                processing_time=0.0,
                metadata={"person": person_name}
            )

        # Custom prompt for profile generation
        context = self.format_context(search_results)
        profile_query = f"""Crée un profil complet de {person_name} basé sur les conversations.

Structure attendue:
1. Informations personnelles (famille, anniversaires, centres d'intérêt)
2. Informations professionnelles (poste, entreprise, projets)
3. Style de communication et personnalité
4. Préoccupations et objectifs actuels
5. Suggestions pour les prochaines interactions"""

        answer = self.generate_response(profile_query, context, max_new_tokens=1024)

        confidence = self._calculate_confidence(search_results)

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=0.0,
            metadata={"person": person_name, "profile_type": "comprehensive"}
        )

class MeetingSuggestionChain(BaseRAGChain):
    """Chain for generating meeting preparation suggestions"""

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

    def format_context(self, search_results: List[SearchResult]) -> str:
        context_parts = []

        for result in search_results:
            chunk = result.chunk
            date = chunk.metadata.get('date', '')[:10]
            context_parts.append(f"""
[{date}] {chunk.text}
""")

        return '\n'.join(context_parts)

    def generate_meeting_prep(self, person_name: str, meeting_context: str = "") -> RAGResponse:
        """Generate meeting preparation suggestions"""
        query = f"Préparer une réunion avec {person_name}"

        # Search for recent conversations
        search_results = self.search_engine.search_by_person(
            person_name,
            query_text=query,
            max_results=15
        )

        context = self.format_context(search_results)

        prep_query = f"""Prépare une liste de suggestions pour une prochaine réunion avec {person_name}.
{f'Contexte de la réunion: {meeting_context}' if meeting_context else ''}

Structure attendue:
1. Points personnels à mentionner (anniversaires, famille, événements récents)
2. Sujets professionnels à aborder (projets, objectifs, défis)
3. Questions à poser pour maintenir l'engagement
4. Points d'attention ou sujets sensibles à éviter
5. Opportunités de collaboration ou d'aide à proposer"""

        answer = self.generate_response(prep_query, context, max_new_tokens=768)

        confidence = self._calculate_confidence(search_results)

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=0.0,
            metadata={
                "person": person_name,
                "meeting_context": meeting_context,
                "suggestion_type": "meeting_prep"
            }
        )

class ProjectAnalysisChain(BaseRAGChain):
    """Chain for analyzing project discussions and progress"""

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

    def format_context(self, search_results: List[SearchResult]) -> str:
        context_parts = []

        for result in search_results:
            chunk = result.chunk
            date = chunk.metadata.get('date', '')[:10]
            participants = ', '.join(chunk.metadata.get('participants', []))
            context_parts.append(f"""
Date: {date} | Participants: {participants}
Discussion: {chunk.text}
---""")

        return '\n'.join(context_parts)

    def analyze_project(self, project_name: str) -> RAGResponse:
        """Analyze a specific project based on conversations"""
        query = f"Analyse du projet {project_name} - avancement, défis, décisions"

        search_results = self.search_engine.search_conversations(
            query,
            max_results=25
        )

        context = self.format_context(search_results)

        analysis_query = f"""Analyse complète du projet {project_name} basée sur les discussions.

Structure attendue:
1. État d'avancement actuel
2. Principales décisions prises
3. Défis et blocages identifiés
4. Parties prenantes et leurs rôles
5. Risques potentiels
6. Recommandations et prochaines étapes"""

        answer = self.generate_response(analysis_query, context, max_new_tokens=1024)

        confidence = self._calculate_confidence(search_results)

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=0.0,
            metadata={
                "project": project_name,
                "analysis_type": "comprehensive"
            }
        )

class TimelineAnalysisChain(BaseRAGChain):
    """Chain for temporal analysis of conversations and relationships"""

    def get_system_prompt(self) -> str:
        return """Tu es un assistant expert en analyse temporelle des relations et des projets.
Ton rôle est d'analyser l'évolution des discussions, relations et projets dans le temps.

Instructions:
- Crée une chronologie claire des événements
- Identifie les tendances et les patterns
- Analyse l'évolution des relations
- Détecte les changements de priorités
- Propose des prédictions basées sur les tendances
- Identifie les moments clés et les tournants"""

    def format_context(self, search_results: List[SearchResult]) -> str:
        # Sort by date for chronological analysis
        sorted_results = sorted(
            search_results,
            key=lambda x: x.chunk.metadata.get('date', ''),
            reverse=False
        )

        context_parts = []
        for result in sorted_results:
            chunk = result.chunk
            date = chunk.metadata.get('date', '')[:10]
            context_parts.append(f"[{date}] {chunk.text}")

        return '\n'.join(context_parts)

    def analyze_timeline(self, subject: str, time_period: str = "") -> RAGResponse:
        """Analyze the timeline of conversations about a subject"""
        query = f"Évolution temporelle des discussions sur {subject}"

        search_results = self.search_engine.search_conversations(
            query,
            max_results=30
        )

        context = self.format_context(search_results)

        timeline_query = f"""Analyse l'évolution temporelle des discussions concernant {subject}.
{f'Période: {time_period}' if time_period else ''}

Structure attendue:
1. Chronologie des événements clés
2. Tendances et patterns identifiés
3. Évolution des priorités et des préoccupations
4. Moments de rupture ou de changement
5. Prédictions et recommandations pour l'avenir"""

        answer = self.generate_response(timeline_query, context, max_new_tokens=1024)

        confidence = self._calculate_confidence(search_results)

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=0.0,
            metadata={
                "subject": subject,
                "analysis_type": "timeline",
                "time_period": time_period
            }
        )

class RAGChainManager:
    """Manager for different RAG chains"""

    def __init__(self, search_engine: ConversationSearchEngine):
        self.search_engine = search_engine

        # Initialize all chains
        self.chains = {
            "conversation_analysis": ConversationAnalysisChain(search_engine),
            "person_profile": PersonProfileChain(search_engine),
            "meeting_suggestion": MeetingSuggestionChain(search_engine),
            "project_analysis": ProjectAnalysisChain(search_engine),
            "timeline_analysis": TimelineAnalysisChain(search_engine)
        }

        logger.info(f"RAGChainManager initialized with {len(self.chains)} chains")

    def get_chain(self, chain_type: str) -> BaseRAGChain:
        """Get a specific chain by type"""
        if chain_type not in self.chains:
            raise ValueError(f"Unknown chain type: {chain_type}")
        return self.chains[chain_type]

    def process_query(self, query: str, chain_type: str = "conversation_analysis", **kwargs) -> RAGResponse:
        """Process a query using the specified chain"""
        chain = self.get_chain(chain_type)
        return chain.process(query, **kwargs)

    def available_chains(self) -> List[str]:
        """Get list of available chain types"""
        return list(self.chains.keys())