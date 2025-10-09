"""
Advanced Entity Extraction System for Conversation Analysis
Optimized for GPU processing without audio transcription
"""

import torch
import spacy
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import re
from pathlib import Path
import json
from geopy.geocoders import Nominatim
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import dateparser
from collections import defaultdict

@dataclass
class ExtractedEntity:
    """Represents an extracted entity from text"""
    text: str
    entity_type: str
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PersonInfo:
    """Detailed information about a person"""
    name: str
    aliases: List[str] = field(default_factory=list)
    role: Optional[str] = None
    company: Optional[str] = None
    family_members: Dict[str, str] = field(default_factory=dict)  # relation -> name
    birthday: Optional[datetime] = None
    interests: List[str] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)

@dataclass
class ConversationEntities:
    """All entities extracted from a conversation"""
    persons: List[PersonInfo]
    dates: List[Dict[str, Any]]
    locations: List[Dict[str, Any]]
    organizations: List[str]
    projects: List[str]
    personal_info: Dict[str, Any]
    action_items: List[str]
    sentiment_moments: List[Dict[str, Any]]

class GPUEntityExtractor:
    """
    GPU-accelerated entity extraction for conversation analysis
    """

    def __init__(self, device: str = "cuda:0"):
        self.device = device if torch.cuda.is_available() else "cpu"

        # Load spaCy model with GPU support
        self.nlp = spacy.load("fr_core_news_lg")
        if torch.cuda.is_available():
            spacy.prefer_gpu()

        # Load transformer NER model for French
        self.ner_pipeline = pipeline(
            "token-classification",
            model="Jean-Baptiste/camembert-ner-with-dates",
            device=0 if torch.cuda.is_available() else -1,
            aggregation_strategy="simple"
        )

        # Initialize specialized extractors
        self.date_extractor = DateExtractor()
        self.location_extractor = LocationExtractor()
        self.relationship_extractor = RelationshipExtractor()
        self.personal_info_extractor = PersonalInfoExtractor()

        # Patterns for specific extractions
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for entity extraction"""

        # Family relationships
        self.family_patterns = {
            'spouse': r'(?:ma femme|mon mari|mon épouse|mon époux|ma compagne|mon compagnon)\s+(\w+)',
            'children': r'(?:mon fils|ma fille|mes enfants?)\s+(\w+)',
            'parents': r'(?:ma mère|mon père|mes parents)\s+(\w+)'
        }

        # Project patterns
        self.project_pattern = re.compile(
            r'(?:projet|initiative|programme|mission)\s+([A-Z]\w+)',
            re.IGNORECASE
        )

        # Action item patterns
        self.action_patterns = [
            re.compile(r'(?:je vais|nous allons|il faut|on doit)\s+(.+?)(?:\.|,|$)', re.IGNORECASE),
            re.compile(r'(?:TODO|À faire|Action):\s*(.+?)(?:\.|$)', re.IGNORECASE)
        ]

    def extract_all_entities(self, text: str, metadata: Optional[Dict] = None) -> ConversationEntities:
        """
        Main extraction method - processes text and extracts all entity types
        """
        # Process with spaCy
        doc = self.nlp(text)

        # Process with transformer NER
        ner_results = self.ner_pipeline(text)

        # Extract different entity types
        persons = self._extract_persons(doc, ner_results, text)
        dates = self._extract_dates(text, metadata)
        locations = self._extract_locations(doc, text, metadata)
        organizations = self._extract_organizations(doc, ner_results)
        projects = self._extract_projects(text)
        personal_info = self._extract_personal_info(text)
        action_items = self._extract_action_items(text)
        sentiment_moments = self._analyze_sentiment_moments(doc)

        return ConversationEntities(
            persons=persons,
            dates=dates,
            locations=locations,
            organizations=organizations,
            projects=projects,
            personal_info=personal_info,
            action_items=action_items,
            sentiment_moments=sentiment_moments
        )

    def _extract_persons(self, doc, ner_results, text: str) -> List[PersonInfo]:
        """Extract person entities with detailed information"""
        persons = {}

        # From spaCy
        for ent in doc.ents:
            if ent.label_ == "PER":
                if ent.text not in persons:
                    persons[ent.text] = PersonInfo(name=ent.text)

        # From transformer NER
        for entity in ner_results:
            if entity['entity_group'] in ['PER', 'PERSON']:
                name = entity['word'].strip()
                if name and name not in persons:
                    persons[name] = PersonInfo(name=name)

        # Extract additional person info
        for person_name, person_info in persons.items():
            # Find role/title
            role_pattern = rf'{re.escape(person_name)},?\s*(?:le|la|l\')?\s*(\w+(?:\s+\w+)?)'
            role_match = re.search(role_pattern, text, re.IGNORECASE)
            if role_match:
                person_info.role = role_match.group(1)

            # Extract family relationships
            self._extract_family_relations(text, person_info)

            # Extract birthday if mentioned
            birthday_pattern = rf'anniversaire\s+de\s+{re.escape(person_name)}.*?(\d{{1,2}}\s+\w+)'
            birthday_match = re.search(birthday_pattern, text, re.IGNORECASE)
            if birthday_match:
                date = dateparser.parse(birthday_match.group(1), languages=['fr'])
                if date:
                    person_info.birthday = date

        return list(persons.values())

    def _extract_dates(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Extract dates and temporal references"""
        dates = []

        # Use dateparser for flexible date extraction
        date_strings = re.findall(
            r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{2,4}|'
            r'lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|'
            r'demain|après-demain|hier|avant-hier|'
            r'semaine prochaine|mois prochain|année prochaine)\b',
            text, re.IGNORECASE
        )

        base_date = datetime.now()
        if metadata and 'conversation_date' in metadata:
            base_date = datetime.fromisoformat(metadata['conversation_date'])

        for date_str in date_strings:
            parsed_date = dateparser.parse(
                date_str,
                languages=['fr'],
                settings={'RELATIVE_BASE': base_date}
            )

            if parsed_date:
                # Determine context
                context = self._get_date_context(text, date_str)
                dates.append({
                    'original_text': date_str,
                    'parsed_date': parsed_date.isoformat(),
                    'context': context,
                    'type': self._classify_date_type(context)
                })

        return dates

    def _extract_locations(self, doc, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Extract locations with GPS coordinates if available"""
        locations = []

        # Extract from spaCy
        for ent in doc.ents:
            if ent.label_ in ["LOC", "GPE"]:
                location = {
                    'name': ent.text,
                    'type': 'location'
                }

                # Check if GPS coordinates are mentioned nearby
                gps_pattern = r'(\d+\.\d+)[,\s]+(\d+\.\d+)'
                gps_match = re.search(gps_pattern, text[max(0, ent.start_char-50):ent.end_char+50])
                if gps_match:
                    location['gps'] = {
                        'latitude': float(gps_match.group(1)),
                        'longitude': float(gps_match.group(2))
                    }

                locations.append(location)

        # Add metadata location if available
        if metadata and 'gps' in metadata:
            locations.append({
                'name': 'Conversation location',
                'type': 'metadata',
                'gps': metadata['gps']
            })

        return locations

    def _extract_organizations(self, doc, ner_results) -> List[str]:
        """Extract organization names"""
        orgs = set()

        # From spaCy
        for ent in doc.ents:
            if ent.label_ == "ORG":
                orgs.add(ent.text)

        # From transformer NER
        for entity in ner_results:
            if entity['entity_group'] in ['ORG', 'ORGANIZATION']:
                orgs.add(entity['word'].strip())

        return list(orgs)

    def _extract_projects(self, text: str) -> List[str]:
        """Extract project names and initiatives"""
        projects = []
        matches = self.project_pattern.findall(text)
        for match in matches:
            if len(match) > 2:  # Filter out too short matches
                projects.append(match)
        return list(set(projects))

    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items and todos"""
        action_items = []
        for pattern in self.action_patterns:
            matches = pattern.findall(text)
            action_items.extend(matches)
        return list(set(action_items))

    def _extract_personal_info(self, text: str) -> Dict[str, Any]:
        """Extract personal information like hobbies, preferences"""
        personal_info = {
            'hobbies': [],
            'preferences': [],
            'important_dates': []
        }

        # Hobby patterns
        hobby_patterns = [
            r'(?:j\'aime|je préfère|passion pour|fan de|adore)\s+(?:le |la |les )?(\w+(?:\s+\w+)?)',
            r'(?:hobby|loisir|passe-temps).*?(?:est|sont)\s+(?:le |la |les )?(\w+(?:\s+\w+)?)'
        ]

        for pattern in hobby_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            personal_info['hobbies'].extend(matches)

        return personal_info

    def _extract_family_relations(self, text: str, person_info: PersonInfo):
        """Extract family relationships for a person"""
        for relation, pattern in self.family_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if relation == 'children':
                    if 'children' not in person_info.family_members:
                        person_info.family_members['children'] = []
                    person_info.family_members['children'].append(match)
                else:
                    person_info.family_members[relation] = match

    def _get_date_context(self, text: str, date_str: str) -> str:
        """Get context around a date mention"""
        index = text.lower().find(date_str.lower())
        if index != -1:
            start = max(0, index - 50)
            end = min(len(text), index + len(date_str) + 50)
            return text[start:end]
        return ""

    def _classify_date_type(self, context: str) -> str:
        """Classify the type of date (meeting, deadline, birthday, etc.)"""
        context_lower = context.lower()

        if any(word in context_lower for word in ['réunion', 'meeting', 'rendez-vous']):
            return 'meeting'
        elif any(word in context_lower for word in ['deadline', 'échéance', 'livraison']):
            return 'deadline'
        elif any(word in context_lower for word in ['anniversaire', 'birthday']):
            return 'birthday'
        elif any(word in context_lower for word in ['projet', 'lancement', 'début']):
            return 'project_milestone'
        else:
            return 'general'

    def _analyze_sentiment_moments(self, doc) -> List[Dict[str, Any]]:
        """Analyze sentiment at different moments in the conversation"""
        sentiment_moments = []

        # Simple sentiment analysis based on word polarity
        positive_words = {'heureux', 'content', 'satisfait', 'excellent', 'parfait', 'super'}
        negative_words = {'inquiet', 'problème', 'difficile', 'compliqué', 'stress', 'urgent'}

        sentences = list(doc.sents)
        for i, sent in enumerate(sentences):
            sent_text = sent.text.lower()

            positive_score = sum(1 for word in positive_words if word in sent_text)
            negative_score = sum(1 for word in negative_words if word in sent_text)

            if positive_score > 0 or negative_score > 0:
                sentiment = 'positive' if positive_score > negative_score else 'negative'
                sentiment_moments.append({
                    'sentence_index': i,
                    'text': sent.text,
                    'sentiment': sentiment,
                    'confidence': max(positive_score, negative_score) / len(sent_text.split())
                })

        return sentiment_moments

    def batch_extract(self, texts: List[str], batch_size: int = 32) -> List[ConversationEntities]:
        """Process multiple texts in batches for efficiency"""
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = []

            # Process batch with transformer NER
            ner_batch = self.ner_pipeline(batch)

            for j, text in enumerate(batch):
                doc = self.nlp(text)
                ner_results = ner_batch[j] if j < len(ner_batch) else []

                entities = self.extract_all_entities(text)
                batch_results.append(entities)

            results.extend(batch_results)

        return results


class DateExtractor:
    """Specialized date extraction and normalization"""

    def __init__(self):
        self.date_patterns = [
            # ISO format
            r'\d{4}-\d{2}-\d{2}',
            # European format
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            # Written format
            r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{2,4}',
            # Relative dates
            r'(?:demain|après-demain|hier|avant-hier|la semaine prochaine|le mois prochain)'
        ]

    def extract(self, text: str, base_date: Optional[datetime] = None) -> List[Dict]:
        """Extract all dates from text"""
        if base_date is None:
            base_date = datetime.now()

        dates = []
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group()
                parsed = dateparser.parse(
                    date_str,
                    languages=['fr'],
                    settings={'RELATIVE_BASE': base_date}
                )
                if parsed:
                    dates.append({
                        'original': date_str,
                        'parsed': parsed,
                        'position': match.span()
                    })

        return dates


class LocationExtractor:
    """Extract and geocode locations"""

    def __init__(self):
        self.geolocator = Nominatim(user_agent="rag_conversation_app")
        self.gps_pattern = re.compile(r'(\d+\.\d+)[,\s]+(\d+\.\d+)')

    def extract(self, text: str) -> List[Dict]:
        """Extract locations with optional geocoding"""
        locations = []

        # Extract GPS coordinates
        gps_matches = self.gps_pattern.findall(text)
        for lat, lon in gps_matches:
            locations.append({
                'type': 'gps',
                'coordinates': {
                    'latitude': float(lat),
                    'longitude': float(lon)
                }
            })

        return locations


class RelationshipExtractor:
    """Extract relationships between entities"""

    def __init__(self):
        self.relationship_patterns = {
            'manages': r'(\w+)\s+(?:manage|dirige|supervise)\s+(\w+)',
            'works_with': r'(\w+)\s+(?:travaille avec|collabore avec)\s+(\w+)',
            'reports_to': r'(\w+)\s+(?:rapporte à|report to)\s+(\w+)',
            'married_to': r'(\w+)\s+(?:marié à|époux de|épouse de)\s+(\w+)'
        }

    def extract(self, text: str) -> List[Dict]:
        """Extract relationships between people"""
        relationships = []

        for rel_type, pattern in self.relationship_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                relationships.append({
                    'type': rel_type,
                    'source': match[0],
                    'target': match[1]
                })

        return relationships


class PersonalInfoExtractor:
    """Extract personal information and preferences"""

    def __init__(self):
        self.info_patterns = {
            'hobbies': [
                r'(?:hobby|loisir|passion|j\'aime|adore).*?(\w+(?:\s+\w+)?)',
                r'(?:pratique|fait du|joue au)\s+(\w+(?:\s+\w+)?)'
            ],
            'dislikes': [
                r'(?:n\'aime pas|déteste|évite)\s+(?:le |la |les )?(\w+(?:\s+\w+)?)'
            ],
            'goals': [
                r'(?:objectif|but|ambition|souhaite).*?(\w+(?:\s+\w+)?)'
            ]
        }

    def extract(self, text: str) -> Dict[str, List[str]]:
        """Extract personal preferences and information"""
        personal_info = defaultdict(list)

        for category, patterns in self.info_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                personal_info[category].extend(matches)

        # Remove duplicates
        for category in personal_info:
            personal_info[category] = list(set(personal_info[category]))

        return dict(personal_info)