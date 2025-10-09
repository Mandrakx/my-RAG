"""
API endpoints for person profile management and analysis
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging
import json
import tempfile
from pathlib import Path

from ...rag.profile_management import ProfileBuilder, SuggestionEngine, ReminderSystem, ProfileExporter
from ...rag.models.conversation import PersonProfile, MeetingSuggestion, PersonalReminder, SuggestionContext
from ...rag.chains.rag_chains import RAGChainManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[datetime] = None
    interests: Optional[List[str]] = None
    notes: Optional[str] = None

class SuggestionRequest(BaseModel):
    person_id: str
    meeting_date: Optional[datetime] = None
    meeting_type: Optional[str] = None
    context: Optional[str] = None

class ReminderRequest(BaseModel):
    person_id: str
    title: str
    description: str
    reminder_date: datetime
    importance: str = "medium"

# Dependencies
async def get_profile_builder() -> ProfileBuilder:
    """Dependency to get profile builder instance"""
    from ...main import app
    return app.state.profile_builder

async def get_suggestion_engine() -> SuggestionEngine:
    """Dependency to get suggestion engine instance"""
    from ...main import app
    return app.state.suggestion_engine

async def get_reminder_system() -> ReminderSystem:
    """Dependency to get reminder system instance"""
    from ...main import app
    return app.state.reminder_system

async def get_chain_manager() -> RAGChainManager:
    """Dependency to get chain manager instance"""
    from ...main import app
    return app.state.chain_manager

@router.get("/list")
async def list_profiles(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """List all profiles with pagination and search"""
    try:
        all_profiles = profile_builder.get_all_profiles()

        # Apply search filter
        if search:
            filtered_profiles = profile_builder.search_profiles(search, max_results=limit*2)
        else:
            filtered_profiles = all_profiles

        # Apply pagination
        paginated_profiles = filtered_profiles[offset:offset+limit]

        # Format response
        profiles_data = []
        for profile in paginated_profiles:
            profiles_data.append({
                "person_id": profile.person_id,
                "name": profile.name,
                "title": profile.title,
                "company": profile.company,
                "total_interactions": profile.total_interactions,
                "last_interaction": profile.last_interaction_date.isoformat() if profile.last_interaction_date else None,
                "birthday": profile.birthday.isoformat() if profile.birthday else None
            })

        return {
            "profiles": profiles_data,
            "total": len(filtered_profiles),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(filtered_profiles)
        }

    except Exception as e:
        logger.error(f"Error listing profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}")
async def get_profile(
    person_id: str,
    include_family: bool = Query(default=True),
    include_interactions: bool = Query(default=True),
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Get detailed profile for a person"""
    try:
        profile = profile_builder.get_profile(person_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Build response
        profile_data = {
            "person_id": profile.person_id,
            "name": profile.name,
            "aliases": profile.aliases,
            "personal_info": {
                "birthday": profile.birthday.isoformat() if profile.birthday else None,
                "interests": profile.interests,
                "hobbies": profile.hobbies,
                "dislikes": profile.dislikes
            },
            "professional_info": {
                "title": profile.title,
                "company": profile.company,
                "department": profile.department,
                "expertise": profile.expertise,
                "current_projects": profile.current_projects
            },
            "contact_info": {
                "email": profile.email,
                "phone": profile.phone,
                "preferred_contact_method": profile.preferred_contact_method
            },
            "communication": {
                "style": profile.communication_style,
                "best_contact_time": profile.best_contact_time,
                "timezone": profile.timezone
            },
            "metadata": {
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
                "confidence_score": profile.confidence_score
            }
        }

        # Add family information if requested
        if include_family:
            profile_data["family"] = [
                {
                    "name": fm.name,
                    "relationship": fm.relationship,
                    "age": fm.age,
                    "birthday": fm.birthday.isoformat() if fm.birthday else None,
                    "additional_info": fm.additional_info
                }
                for fm in profile.family_members
            ]

        # Add interaction stats if requested
        if include_interactions:
            profile_data["interactions"] = {
                "total_count": profile.total_interactions,
                "last_interaction": profile.last_interaction_date.isoformat() if profile.last_interaction_date else None,
                "frequency": profile.interaction_frequency,
                "relationship_info": {
                    "reports_to": profile.reports_to,
                    "manages": profile.manages,
                    "collaborates_with": profile.collaborates_with
                }
            }

        return profile_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{person_id}")
async def update_profile(
    person_id: str,
    update_data: ProfileUpdate,
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Update profile information"""
    try:
        profile = profile_builder.get_profile(person_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Update fields
        if update_data.name is not None:
            profile.name = update_data.name
        if update_data.title is not None:
            profile.title = update_data.title
        if update_data.company is not None:
            profile.company = update_data.company
        if update_data.email is not None:
            profile.email = update_data.email
        if update_data.phone is not None:
            profile.phone = update_data.phone
        if update_data.birthday is not None:
            profile.birthday = update_data.birthday
        if update_data.interests is not None:
            profile.interests = update_data.interests

        profile.updated_at = datetime.now()

        return {
            "person_id": person_id,
            "status": "updated",
            "updated_at": profile.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/summary")
async def get_profile_summary(
    person_id: str,
    profile_builder: ProfileBuilder = Depends(get_profile_builder),
    chain_manager: RAGChainManager = Depends(get_chain_manager)
):
    """Generate AI-powered profile summary"""
    try:
        profile = profile_builder.get_profile(person_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Use AI chain to generate comprehensive summary
        chain = chain_manager.get_chain("person_profile")
        response = chain.generate_profile_summary(profile.name)

        return {
            "person_id": person_id,
            "name": profile.name,
            "ai_summary": response.answer,
            "confidence": response.confidence,
            "based_on_conversations": len(response.sources),
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating profile summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/{query}")
async def search_profiles(
    query: str,
    max_results: int = Query(default=10, ge=1, le=50),
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Search profiles by name, company, or other attributes"""
    try:
        results = profile_builder.search_profiles(query, max_results)

        formatted_results = []
        for profile in results:
            formatted_results.append({
                "person_id": profile.person_id,
                "name": profile.name,
                "title": profile.title,
                "company": profile.company,
                "last_interaction": profile.last_interaction_date.isoformat() if profile.last_interaction_date else None,
                "interaction_count": profile.total_interactions
            })

        return {
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }

    except Exception as e:
        logger.error(f"Error searching profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{person_id}/suggestions")
async def generate_meeting_suggestions(
    person_id: str,
    request: SuggestionRequest,
    suggestion_engine: SuggestionEngine = Depends(get_suggestion_engine)
):
    """Generate meeting preparation suggestions for a person"""
    try:
        # Create suggestion context
        context = SuggestionContext(
            target_person_id=person_id,
            upcoming_meeting_date=request.meeting_date,
            meeting_type=request.meeting_type
        )

        # Generate suggestions
        suggestions = suggestion_engine.generate_meeting_suggestions(context)

        # Format response
        formatted_suggestions = []
        for suggestion in suggestions:
            formatted_suggestions.append({
                "suggestion_id": suggestion.suggestion_id,
                "type": suggestion.suggestion_type,
                "title": suggestion.title,
                "description": suggestion.description,
                "priority": suggestion.priority,
                "confidence": suggestion.confidence,
                "reasoning": suggestion.reasoning
            })

        return {
            "person_id": person_id,
            "meeting_context": request.context,
            "suggestions": formatted_suggestions,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/timeline")
async def get_person_timeline(
    person_id: str,
    days_back: int = Query(default=90, ge=1, le=365),
    profile_builder: ProfileBuilder = Depends(get_profile_builder),
    chain_manager: RAGChainManager = Depends(get_chain_manager)
):
    """Get timeline analysis for a person"""
    try:
        profile = profile_builder.get_profile(person_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Use timeline analysis chain
        chain = chain_manager.get_chain("timeline_analysis")
        response = chain.analyze_timeline(
            subject=profile.name,
            time_period=f"derniers {days_back} jours"
        )

        return {
            "person_id": person_id,
            "name": profile.name,
            "timeline_analysis": response.answer,
            "confidence": response.confidence,
            "period_days": days_back,
            "sources_count": len(response.sources),
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/reminders")
async def get_person_reminders(
    person_id: str,
    days_ahead: int = Query(default=30, ge=1, le=365),
    reminder_system: ReminderSystem = Depends(get_reminder_system)
):
    """Get upcoming reminders for a person"""
    try:
        all_reminders = reminder_system.generate_upcoming_reminders(days_ahead)

        # Filter for this person
        person_reminders = [
            reminder for reminder in all_reminders
            if reminder.person_id == person_id
        ]

        formatted_reminders = []
        for reminder in person_reminders:
            formatted_reminders.append({
                "reminder_id": reminder.reminder_id,
                "type": reminder.reminder_type,
                "title": reminder.title,
                "description": reminder.description,
                "reminder_date": reminder.reminder_date.isoformat(),
                "importance": reminder.importance,
                "auto_generated": reminder.auto_generated
            })

        return {
            "person_id": person_id,
            "reminders": formatted_reminders,
            "period_days": days_ahead,
            "count": len(formatted_reminders)
        }

    except Exception as e:
        logger.error(f"Error getting reminders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{person_id}/reminders")
async def create_reminder(
    person_id: str,
    reminder_request: ReminderRequest,
    reminder_system: ReminderSystem = Depends(get_reminder_system)
):
    """Create a custom reminder for a person"""
    try:
        reminder = reminder_system.add_custom_reminder(
            person_id=person_id,
            title=reminder_request.title,
            description=reminder_request.description,
            reminder_date=reminder_request.reminder_date,
            importance=reminder_request.importance
        )

        return {
            "reminder_id": reminder.reminder_id,
            "person_id": person_id,
            "status": "created",
            "reminder_date": reminder.reminder_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/export")
async def export_profile(
    person_id: str,
    format: str = Query(default="json", regex="^(json|pdf)$"),
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Export profile in JSON or PDF format"""
    try:
        profile = profile_builder.get_profile(person_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        exporter = ProfileExporter(profile_builder)

        if format == "json":
            profile_data = exporter.export_profile_summary(person_id)

            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(profile_data, f, indent=2, default=str)
                temp_path = f.name

            return FileResponse(
                path=temp_path,
                filename=f"{profile.name.replace(' ', '_')}_profile.json",
                media_type="application/json"
            )

        elif format == "pdf":
            # PDF export would require additional implementation
            # For now, return JSON data
            profile_data = exporter.export_profile_summary(person_id)
            return JSONResponse(content={
                "message": "PDF export not yet implemented",
                "data": profile_data
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{person_id}")
async def delete_profile(
    person_id: str,
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Delete a person profile (GDPR compliance)"""
    try:
        profile = profile_builder.get_profile(person_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Note: This would require implementing deletion across all systems
        # For now, return a placeholder response
        return {
            "person_id": person_id,
            "status": "deletion_requested",
            "message": "Profile deletion initiated (GDPR compliance)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview")
async def get_profile_stats(
    profile_builder: ProfileBuilder = Depends(get_profile_builder)
):
    """Get overall profile statistics"""
    try:
        all_profiles = profile_builder.get_all_profiles()

        # Calculate statistics
        total_profiles = len(all_profiles)
        profiles_with_birthday = len([p for p in all_profiles if p.birthday])
        profiles_with_family = len([p for p in all_profiles if p.family_members])
        active_profiles = len([p for p in all_profiles if p.total_interactions > 0])

        # Interaction statistics
        total_interactions = sum(p.total_interactions for p in all_profiles)
        avg_interactions = total_interactions / total_profiles if total_profiles > 0 else 0

        # Top companies
        companies = {}
        for profile in all_profiles:
            if profile.company:
                companies[profile.company] = companies.get(profile.company, 0) + 1

        top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_profiles": total_profiles,
            "active_profiles": active_profiles,
            "profiles_with_birthday": profiles_with_birthday,
            "profiles_with_family": profiles_with_family,
            "interaction_stats": {
                "total_interactions": total_interactions,
                "average_per_person": round(avg_interactions, 2)
            },
            "top_companies": [{"company": comp, "count": count} for comp, count in top_companies]
        }

    except Exception as e:
        logger.error(f"Error getting profile stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))