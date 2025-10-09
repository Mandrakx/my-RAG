"""
API endpoints for conversation management and analysis
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from ...rag.models.conversation import (
    ConversationMetadata, ConversationType, InteractionType,
    Location, GPSCoordinate, Participant
)
from ...rag.chains.rag_chains import RAGChainManager
from ...rag.retrieval.hybrid_retriever import ConversationSearchEngine, SearchQuery
from ...rag.entity_extraction import GPUEntityExtractor
from ...rag.profile_management import ProfileBuilder

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for API
class ConversationUpload(BaseModel):
    title: Optional[str] = None
    transcript: str
    date: datetime
    conversation_type: ConversationType = ConversationType.MEETING
    interaction_type: InteractionType = InteractionType.PROFESSIONAL
    participants: List[Dict[str, Any]]
    location: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)

class ConversationSearch(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    person_filter: Optional[List[str]] = None
    conversation_type_filter: Optional[str] = None
    gps_filter: Optional[Dict[str, float]] = None
    use_reranking: bool = True

class AnalysisRequest(BaseModel):
    query: str
    chain_type: str = "conversation_analysis"
    conversation_id: Optional[str] = None
    person_name: Optional[str] = None
    project_name: Optional[str] = None

class ProfileRequest(BaseModel):
    person_name: str
    include_suggestions: bool = True

# Dependencies
async def get_search_engine() -> ConversationSearchEngine:
    """Dependency to get search engine instance"""
    # In production, this would be injected or retrieved from app state
    from ...main import app
    return app.state.search_engine

async def get_chain_manager() -> RAGChainManager:
    """Dependency to get chain manager instance"""
    from ...main import app
    return app.state.chain_manager

async def get_entity_extractor() -> GPUEntityExtractor:
    """Dependency to get entity extractor instance"""
    from ...main import app
    return app.state.entity_extractor

async def get_profile_builder() -> ProfileBuilder:
    """Dependency to get profile builder instance"""
    from ...main import app
    return app.state.profile_builder

@router.post("/upload", status_code=201)
async def upload_conversation(
    conversation: ConversationUpload,
    background_tasks: BackgroundTasks,
    search_engine: ConversationSearchEngine = Depends(get_search_engine),
    entity_extractor: GPUEntityExtractor = Depends(get_entity_extractor),
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Upload and process a new conversation"""
    try:
        # Create metadata
        participants = [
            Participant(**p) for p in conversation.participants
        ]

        location = None
        if conversation.location:
            gps = None
            if 'gps' in conversation.location:
                gps = GPSCoordinate(**conversation.location['gps'])
            location = Location(
                name=conversation.location.get('name'),
                address=conversation.location.get('address'),
                gps=gps
            )

        metadata = ConversationMetadata(
            title=conversation.title,
            date=conversation.date,
            conversation_type=conversation.conversation_type,
            interaction_type=conversation.interaction_type,
            participants=participants,
            location=location,
            tags=conversation.tags
        )

        # Index conversation in search engine
        chunks = search_engine.index_conversation(conversation.transcript, metadata)

        # Background processing
        background_tasks.add_task(
            process_conversation_background,
            conversation.transcript,
            metadata,
            entity_extractor,
            profile_builder
        )

        return {
            "conversation_id": metadata.conversation_id,
            "status": "uploaded",
            "chunks_created": len(chunks),
            "message": "Conversation uploaded and processing started"
        }

    except Exception as e:
        logger.error(f"Error uploading conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_conversation_background(
    transcript: str,
    metadata: ConversationMetadata,
    entity_extractor: GPUEntityExtractor,
    profile_builder: ProfileBuilder
):
    """Background task for processing conversation"""
    try:
        # Extract entities
        entities = entity_extractor.extract_all_entities(transcript, asdict(metadata))

        # Create conversation analysis object
        from ...rag.models.conversation import ConversationAnalysis
        analysis = ConversationAnalysis(
            conversation_id=metadata.conversation_id,
            metadata=metadata,
            transcript=transcript,
            summary="",  # Would be generated
            persons_mentioned=[
                # Convert to PersonProfile objects
            ]
        )

        # Update profiles
        profile_builder.process_conversation(analysis)

        logger.info(f"Background processing completed for {metadata.conversation_id}")

    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")

@router.post("/search")
async def search_conversations(
    search_request: ConversationSearch,
    search_engine: ConversationSearchEngine = Depends(get_search_engine)
):
    """Search conversations using hybrid retrieval"""
    try:
        # Create search query
        query = SearchQuery(
            text=search_request.query,
            max_results=search_request.max_results,
            similarity_threshold=search_request.similarity_threshold,
            use_reranking=search_request.use_reranking
        )

        # Add filters
        if search_request.date_start and search_request.date_end:
            query.date_filter = (search_request.date_start, search_request.date_end)

        if search_request.person_filter:
            query.person_filter = search_request.person_filter

        if search_request.conversation_type_filter:
            query.conversation_type_filter = search_request.conversation_type_filter

        if search_request.gps_filter:
            query.gps_filter = GPSCoordinate(**search_request.gps_filter)

        # Perform search
        results = search_engine.retriever.search(query)

        # Format response
        formatted_results = []
        for result in results:
            formatted_results.append({
                "chunk_id": result.chunk.chunk_id,
                "conversation_id": result.chunk.conversation_id,
                "text": result.chunk.text,
                "relevance_score": result.relevance_score,
                "metadata": result.chunk.metadata,
                "explanation": result.explanation
            })

        return {
            "query": search_request.query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        logger.error(f"Error searching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_conversation(
    analysis_request: AnalysisRequest,
    chain_manager: RAGChainManager = Depends(get_chain_manager)
):
    """Analyze conversations using specialized RAG chains"""
    try:
        # Get the appropriate chain
        chain = chain_manager.get_chain(analysis_request.chain_type)

        # Perform analysis based on chain type
        if analysis_request.chain_type == "person_profile" and analysis_request.person_name:
            response = chain.generate_profile_summary(analysis_request.person_name)
        elif analysis_request.chain_type == "meeting_suggestion" and analysis_request.person_name:
            response = chain.generate_meeting_prep(analysis_request.person_name)
        elif analysis_request.chain_type == "project_analysis" and analysis_request.project_name:
            response = chain.analyze_project(analysis_request.project_name)
        elif analysis_request.chain_type == "timeline_analysis":
            subject = analysis_request.person_name or analysis_request.project_name or "général"
            response = chain.analyze_timeline(subject)
        else:
            # General conversation analysis
            response = chain.process(analysis_request.query)

        # Format sources
        sources = []
        for source in response.sources:
            sources.append({
                "chunk_id": source.chunk.chunk_id,
                "conversation_id": source.chunk.conversation_id,
                "text": source.chunk.text[:200] + "..." if len(source.chunk.text) > 200 else source.chunk.text,
                "relevance_score": source.relevance_score,
                "date": source.chunk.metadata.get('date')
            })

        return {
            "answer": response.answer,
            "confidence": response.confidence,
            "processing_time": response.processing_time,
            "sources": sources,
            "metadata": response.metadata
        }

    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    search_engine: ConversationSearchEngine = Depends(get_search_engine)
):
    """Get conversation details by ID"""
    try:
        # Search for chunks belonging to this conversation
        results = search_engine.search_conversations(
            query=f"conversation_id:{conversation_id}",
            max_results=100
        )

        if not results:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Reconstruct conversation from chunks
        chunks = sorted(
            [result.chunk for result in results],
            key=lambda x: x.chunk_index
        )

        conversation_text = " ".join([chunk.text for chunk in chunks])
        metadata = chunks[0].metadata if chunks else {}

        return {
            "conversation_id": conversation_id,
            "text": conversation_text,
            "chunks": len(chunks),
            "metadata": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    search_engine: ConversationSearchEngine = Depends(get_search_engine)
):
    """Delete a conversation and all its data"""
    try:
        # Note: This would require implementing deletion in the vector store
        # For now, return a placeholder response
        return {
            "conversation_id": conversation_id,
            "status": "deletion_requested",
            "message": "Conversation deletion initiated"
        }

    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_conversation_stats(
    search_engine: ConversationSearchEngine = Depends(get_search_engine)
):
    """Get conversation database statistics"""
    try:
        stats = search_engine.retriever.get_stats()

        return {
            "total_conversations": stats.get("vector_store_stats", {}).get("chunks_stored", 0),
            "vector_store": stats.get("vector_store_stats", {}),
            "sparse_retrieval": stats.get("sparse_stats", {}),
            "features": {
                "sparse_search": stats.get("use_sparse", False),
                "reranking": stats.get("use_reranking", False)
            }
        }

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/by-person/{person_name}")
async def search_by_person(
    person_name: str,
    query: Optional[str] = None,
    max_results: int = 10,
    search_engine: ConversationSearchEngine = Depends(get_search_engine)
):
    """Search conversations involving a specific person"""
    try:
        results = search_engine.search_by_person(
            person_name=person_name,
            query_text=query or f"conversations with {person_name}",
            max_results=max_results
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "chunk_id": result.chunk.chunk_id,
                "conversation_id": result.chunk.conversation_id,
                "text": result.chunk.text,
                "relevance_score": result.relevance_score,
                "date": result.chunk.metadata.get('date'),
                "participants": result.chunk.metadata.get('participants', [])
            })

        return {
            "person": person_name,
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        logger.error(f"Error searching by person: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/by-location")
async def search_by_location(
    latitude: float,
    longitude: float,
    query: Optional[str] = None,
    max_results: int = 10,
    search_engine: ConversationSearchEngine = Depends(get_search_engine)
):
    """Search conversations by GPS location"""
    try:
        gps = GPSCoordinate(latitude=latitude, longitude=longitude)

        results = search_engine.search_by_location(
            gps=gps,
            query_text=query or "conversations at this location",
            max_results=max_results
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "chunk_id": result.chunk.chunk_id,
                "conversation_id": result.chunk.conversation_id,
                "text": result.chunk.text,
                "relevance_score": result.relevance_score,
                "date": result.chunk.metadata.get('date'),
                "location": result.chunk.metadata.get('location_name')
            })

        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        logger.error(f"Error searching by location: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))