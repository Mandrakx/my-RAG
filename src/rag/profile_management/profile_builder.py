"""
Profile management system for building and maintaining individual profiles
from conversation analysis
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import asdict
from collections import defaultdict, Counter
import logging

from ..models.conversation import (
    PersonProfile, ConversationAnalysis, FamilyMember,
    MeetingSuggestion, PersonalReminder, SuggestionContext
)
from ..entity_extraction import ConversationEntities, PersonInfo

logger = logging.getLogger(__name__)

class ProfileBuilder:
    """
    Builds and maintains comprehensive profiles of individuals
    from multiple conversation analyses
    """

    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.profiles: Dict[str, PersonProfile] = {}
        self.name_to_id_mapping: Dict[str, str] = {}  # name variations -> person_id

    def process_conversation(self, conversation: ConversationAnalysis) -> List[str]:
        """
        Process a conversation and update relevant profiles
        Returns list of updated person IDs
        """
        updated_profiles = set()

        for person_info in conversation.persons_mentioned:
            person_id = self._get_or_create_person_id(person_info.name)
            profile = self._get_or_create_profile(person_id, person_info.name)

            # Update profile with new information
            self._update_profile_from_person_info(profile, person_info)
            self._update_profile_from_conversation(profile, conversation)

            updated_profiles.add(person_id)

        return list(updated_profiles)

    def _get_or_create_person_id(self, name: str) -> str:
        """Get existing person ID or create new one for a name"""
        normalized_name = self._normalize_name(name)

        # Check exact match first
        if normalized_name in self.name_to_id_mapping:
            return self.name_to_id_mapping[normalized_name]

        # Check for similar names (fuzzy matching)
        similar_id = self._find_similar_person(normalized_name)
        if similar_id:
            # Add this name as an alias
            self.name_to_id_mapping[normalized_name] = similar_id
            profile = self.profiles[similar_id]
            if normalized_name not in profile.aliases:
                profile.aliases.append(normalized_name)
            return similar_id

        # Create new person ID
        person_id = str(uuid.uuid4())
        self.name_to_id_mapping[normalized_name] = person_id
        return person_id

    def _get_or_create_profile(self, person_id: str, name: str) -> PersonProfile:
        """Get existing profile or create new one"""
        if person_id not in self.profiles:
            self.profiles[person_id] = PersonProfile(
                person_id=person_id,
                name=self._normalize_name(name),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        return self.profiles[person_id]

    def _update_profile_from_person_info(self, profile: PersonProfile, person_info: PersonInfo):
        """Update profile with information from PersonInfo"""
        profile.updated_at = datetime.now()

        # Update basic info
        if person_info.role and not profile.title:
            profile.title = person_info.role
        if person_info.company and not profile.company:
            profile.company = person_info.company

        # Update family information
        for relation, member_name in person_info.family_members.items():
            if relation == 'children' and isinstance(member_name, list):
                for child_name in member_name:
                    self._add_family_member(profile, child_name, 'child')
            else:
                self._add_family_member(profile, member_name, relation)

        # Update birthday
        if person_info.birthday and not profile.birthday:
            profile.birthday = person_info.birthday

        # Update interests
        profile.interests.extend(person_info.interests)
        profile.interests = list(set(profile.interests))  # Remove duplicates

    def _update_profile_from_conversation(self, profile: PersonProfile, conversation: ConversationAnalysis):
        """Update profile with conversation-level information"""
        profile.total_interactions += 1
        profile.last_interaction_date = conversation.metadata.date

        # Extract projects mentioned in relation to this person
        for project in conversation.projects_mentioned:
            if project not in profile.current_projects:
                profile.current_projects.append(project)

        # Update interaction frequency calculation
        self._calculate_interaction_frequency(profile)

        # Analyze communication style from sentiment
        self._analyze_communication_style(profile, conversation)

    def _add_family_member(self, profile: PersonProfile, member_name: str, relationship: str):
        """Add a family member to the profile"""
        # Check if family member already exists
        existing_member = next(
            (fm for fm in profile.family_members if fm.name.lower() == member_name.lower()),
            None
        )

        if not existing_member:
            family_member = FamilyMember(
                name=member_name,
                relationship=relationship
            )
            profile.family_members.append(family_member)

    def _calculate_interaction_frequency(self, profile: PersonProfile):
        """Calculate and update interaction frequency"""
        if profile.total_interactions < 2:
            return

        # This is simplified - in reality, you'd analyze actual date gaps
        if profile.total_interactions >= 4:
            profile.interaction_frequency = "weekly"
        elif profile.total_interactions >= 2:
            profile.interaction_frequency = "monthly"
        else:
            profile.interaction_frequency = "occasional"

    def _analyze_communication_style(self, profile: PersonProfile, conversation: ConversationAnalysis):
        """Analyze and update communication style based on conversation"""
        # Analyze sentiment patterns
        positive_moments = sum(1 for s in conversation.sentiment_moments if s.sentiment == 'positive')
        negative_moments = sum(1 for s in conversation.sentiment_moments if s.sentiment == 'negative')

        # Simple style analysis
        if positive_moments > negative_moments * 2:
            style_indicator = "positive and enthusiastic"
        elif negative_moments > positive_moments:
            style_indicator = "analytical and cautious"
        else:
            style_indicator = "balanced and professional"

        # Update communication style (could be more sophisticated)
        if not profile.communication_style:
            profile.communication_style = style_indicator

    def _normalize_name(self, name: str) -> str:
        """Normalize name for consistent matching"""
        return ' '.join(name.strip().split()).title()

    def _find_similar_person(self, name: str) -> Optional[str]:
        """Find similar person using fuzzy matching"""
        name_parts = set(name.lower().split())

        for existing_name, person_id in self.name_to_id_mapping.items():
            existing_parts = set(existing_name.lower().split())

            # Check for significant overlap (at least one common part)
            common_parts = name_parts.intersection(existing_parts)
            if len(common_parts) > 0 and len(common_parts) >= min(len(name_parts), len(existing_parts)) * 0.5:
                return person_id

        return None

    def get_profile(self, person_id: str) -> Optional[PersonProfile]:
        """Get profile by person ID"""
        return self.profiles.get(person_id)

    def get_profile_by_name(self, name: str) -> Optional[PersonProfile]:
        """Get profile by name"""
        normalized_name = self._normalize_name(name)
        person_id = self.name_to_id_mapping.get(normalized_name)
        if person_id:
            return self.profiles.get(person_id)
        return None

    def get_all_profiles(self) -> List[PersonProfile]:
        """Get all profiles"""
        return list(self.profiles.values())

    def search_profiles(self, query: str, max_results: int = 10) -> List[PersonProfile]:
        """Search profiles by name, company, or title"""
        query_lower = query.lower()
        results = []

        for profile in self.profiles.values():
            score = 0

            # Name matching
            if query_lower in profile.name.lower():
                score += 3

            # Company matching
            if profile.company and query_lower in profile.company.lower():
                score += 2

            # Title matching
            if profile.title and query_lower in profile.title.lower():
                score += 2

            # Alias matching
            for alias in profile.aliases:
                if query_lower in alias.lower():
                    score += 1

            if score > 0:
                results.append((profile, score))

        # Sort by score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [profile for profile, _ in results[:max_results]]


class SuggestionEngine:
    """
    Generates intelligent suggestions for upcoming meetings
    """

    def __init__(self, profile_builder: ProfileBuilder):
        self.profile_builder = profile_builder
        self.suggestion_templates = self._load_suggestion_templates()

    def generate_meeting_suggestions(self, context: SuggestionContext) -> List[MeetingSuggestion]:
        """Generate suggestions for an upcoming meeting"""
        profile = self.profile_builder.get_profile(context.target_person_id)
        if not profile:
            return []

        suggestions = []

        # Personal check-ins
        suggestions.extend(self._generate_personal_suggestions(profile, context))

        # Professional follow-ups
        suggestions.extend(self._generate_professional_suggestions(profile, context))

        # Project updates
        suggestions.extend(self._generate_project_suggestions(profile, context))

        # Relationship building
        suggestions.extend(self._generate_relationship_suggestions(profile, context))

        # Sort by priority and confidence
        suggestions.sort(key=lambda x: (self._priority_score(x.priority), x.confidence), reverse=True)

        return suggestions[:10]  # Return top 10 suggestions

    def _generate_personal_suggestions(self, profile: PersonProfile, context: SuggestionContext) -> List[MeetingSuggestion]:
        """Generate personal check-in suggestions"""
        suggestions = []

        # Birthday reminders
        if profile.birthday:
            days_to_birthday = self._days_until_birthday(profile.birthday)
            if 0 <= days_to_birthday <= 7:
                suggestions.append(MeetingSuggestion(
                    suggestion_type="personal_check",
                    title="Souhaiter un bon anniversaire",
                    description=f"L'anniversaire de {profile.name} est le {profile.birthday.strftime('%d %B')}",
                    priority="high",
                    reasoning="Mentionner l'anniversaire montre de l'attention et renforce la relation",
                    person_id=profile.person_id,
                    confidence=0.9
                ))

        # Family check-ins
        for family_member in profile.family_members:
            if family_member.relationship == 'child':
                suggestions.append(MeetingSuggestion(
                    suggestion_type="personal_check",
                    title=f"Prendre des nouvelles de {family_member.name}",
                    description=f"Demander comment va {family_member.name}",
                    priority="medium",
                    reasoning="Montrer de l'intérêt pour la famille crée une connexion personnelle",
                    person_id=profile.person_id,
                    confidence=0.7
                ))

        return suggestions

    def _generate_professional_suggestions(self, profile: PersonProfile, context: SuggestionContext) -> List[MeetingSuggestion]:
        """Generate professional follow-up suggestions"""
        suggestions = []

        # Project follow-ups
        for project in profile.current_projects:
            suggestions.append(MeetingSuggestion(
                suggestion_type="project_update",
                title=f"Point sur le projet {project}",
                description=f"Faire le point sur l'avancement du projet {project}",
                priority="high",
                reasoning="Maintenir le suivi des projets en cours",
                person_id=profile.person_id,
                confidence=0.8
            ))

        # Career development
        if profile.title:
            suggestions.append(MeetingSuggestion(
                suggestion_type="professional_development",
                title="Évolution de carrière",
                description="Discuter des objectifs professionnels et des opportunités",
                priority="medium",
                reasoning="Montrer de l'intérêt pour le développement professionnel",
                person_id=profile.person_id,
                confidence=0.6
            ))

        return suggestions

    def _generate_project_suggestions(self, profile: PersonProfile, context: SuggestionContext) -> List[MeetingSuggestion]:
        """Generate project-related suggestions"""
        suggestions = []

        # Shared projects
        for project in context.shared_projects:
            suggestions.append(MeetingSuggestion(
                suggestion_type="project_collaboration",
                title=f"Collaboration sur {project}",
                description=f"Discuter de la collaboration sur le projet {project}",
                priority="high",
                reasoning="Renforcer la collaboration sur les projets communs",
                person_id=profile.person_id,
                confidence=0.8
            ))

        return suggestions

    def _generate_relationship_suggestions(self, profile: PersonProfile, context: SuggestionContext) -> List[MeetingSuggestion]:
        """Generate relationship building suggestions"""
        suggestions = []

        # Interests-based
        for interest in profile.interests:
            suggestions.append(MeetingSuggestion(
                suggestion_type="relationship_building",
                title=f"Discuter de {interest}",
                description=f"Échanger sur l'intérêt commun pour {interest}",
                priority="low",
                reasoning="Les intérêts communs renforcent les relations",
                person_id=profile.person_id,
                confidence=0.5
            ))

        return suggestions

    def _days_until_birthday(self, birthday: datetime) -> int:
        """Calculate days until next birthday"""
        today = datetime.now().date()
        this_year_birthday = birthday.replace(year=today.year).date()

        if this_year_birthday < today:
            this_year_birthday = birthday.replace(year=today.year + 1).date()

        return (this_year_birthday - today).days

    def _priority_score(self, priority: str) -> int:
        """Convert priority to numeric score"""
        priority_scores = {
            "urgent": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_scores.get(priority, 0)

    def _load_suggestion_templates(self) -> Dict[str, Any]:
        """Load suggestion templates (could be from file)"""
        return {
            "personal_check": {
                "birthday": "N'oubliez pas de souhaiter un bon anniversaire à {name}",
                "family": "Prenez des nouvelles de {family_member}",
            },
            "professional": {
                "project": "Faire le point sur {project}",
                "goals": "Discuter des objectifs pour {period}",
            }
        }


class ReminderSystem:
    """
    Manages personal reminders about people
    """

    def __init__(self, profile_builder: ProfileBuilder):
        self.profile_builder = profile_builder
        self.reminders: List[PersonalReminder] = []

    def generate_upcoming_reminders(self, days_ahead: int = 30) -> List[PersonalReminder]:
        """Generate reminders for the next N days"""
        upcoming_reminders = []
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        for profile in self.profile_builder.get_all_profiles():
            # Birthday reminders
            if profile.birthday:
                birthday_this_year = profile.birthday.replace(year=today.year).date()
                if birthday_this_year < today:
                    birthday_this_year = profile.birthday.replace(year=today.year + 1).date()

                if today <= birthday_this_year <= end_date:
                    reminder = PersonalReminder(
                        person_id=profile.person_id,
                        reminder_type="birthday",
                        title=f"Anniversaire de {profile.name}",
                        description=f"N'oubliez pas l'anniversaire de {profile.name}",
                        reminder_date=datetime.combine(birthday_this_year, datetime.min.time()),
                        importance="high"
                    )
                    upcoming_reminders.append(reminder)

            # Follow-up reminders based on last interaction
            if profile.last_interaction_date:
                days_since_last = (datetime.now() - profile.last_interaction_date).days

                # Suggest follow-up based on interaction frequency
                follow_up_days = self._get_follow_up_interval(profile.interaction_frequency)
                if days_since_last >= follow_up_days:
                    follow_up_date = datetime.now() + timedelta(days=1)
                    if follow_up_date.date() <= end_date:
                        reminder = PersonalReminder(
                            person_id=profile.person_id,
                            reminder_type="follow_up",
                            title=f"Reprendre contact avec {profile.name}",
                            description=f"Dernière interaction il y a {days_since_last} jours",
                            reminder_date=follow_up_date,
                            importance="medium"
                        )
                        upcoming_reminders.append(reminder)

        return sorted(upcoming_reminders, key=lambda x: x.reminder_date)

    def _get_follow_up_interval(self, frequency: Optional[str]) -> int:
        """Get follow-up interval based on interaction frequency"""
        intervals = {
            "daily": 3,
            "weekly": 10,
            "monthly": 45,
            "occasional": 90
        }
        return intervals.get(frequency, 60)

    def add_custom_reminder(self, person_id: str, title: str, description: str,
                           reminder_date: datetime, importance: str = "medium") -> PersonalReminder:
        """Add a custom reminder"""
        reminder = PersonalReminder(
            person_id=person_id,
            reminder_type="custom",
            title=title,
            description=description,
            reminder_date=reminder_date,
            importance=importance,
            auto_generated=False
        )
        self.reminders.append(reminder)
        return reminder


class ProfileExporter:
    """
    Export profiles in various formats
    """

    def __init__(self, profile_builder: ProfileBuilder):
        self.profile_builder = profile_builder

    def export_profile_summary(self, person_id: str) -> Dict[str, Any]:
        """Export a profile summary as dictionary"""
        profile = self.profile_builder.get_profile(person_id)
        if not profile:
            return {}

        return {
            "personal_info": {
                "name": profile.name,
                "title": profile.title,
                "company": profile.company,
                "birthday": profile.birthday.isoformat() if profile.birthday else None,
                "family_members": [asdict(fm) for fm in profile.family_members]
            },
            "professional_info": {
                "expertise": profile.expertise,
                "current_projects": profile.current_projects,
                "reports_to": profile.reports_to,
                "manages": profile.manages
            },
            "interaction_stats": {
                "total_interactions": profile.total_interactions,
                "last_interaction": profile.last_interaction_date.isoformat() if profile.last_interaction_date else None,
                "frequency": profile.interaction_frequency
            },
            "personal_insights": {
                "interests": profile.interests,
                "hobbies": profile.hobbies,
                "communication_style": profile.communication_style
            }
        }

    def export_all_profiles(self) -> Dict[str, Any]:
        """Export all profiles"""
        return {
            profile.person_id: self.export_profile_summary(profile.person_id)
            for profile in self.profile_builder.get_all_profiles()
        }