"""
Named Entity Recognition (NER) for conversations
Extracts persons, locations, organizations, dates
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import spacy

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Entity types"""
    PERSON = "PER"
    LOCATION = "LOC"
    ORGANIZATION = "ORG"
    MISC = "MISC"
    DATE = "DATE"
    TIME = "TIME"


@dataclass
class Entity:
    """Extracted entity"""
    text: str
    type: EntityType
    start: int
    end: int
    confidence: float
    context: str = ""


class EntityExtractor:
    """
    Extract named entities from conversation turns
    Supports French and multilingual models
    """

    def __init__(
        self,
        model_name: str = "camembert/camembert-ner",
        device: str = "cuda",
        use_spacy: bool = False
    ):
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.use_spacy = use_spacy

        if use_spacy:
            self._load_spacy_model()
        else:
            self._load_transformer_model()

        logger.info(f"Initialized EntityExtractor: {model_name}, device: {self.device}")

    def _load_transformer_model(self):
        """Load transformer-based NER model"""
        logger.info(f"Loading NER model: {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        self.model.to(self.device)
        self.model.eval()

        # Create pipeline
        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1,
            aggregation_strategy="simple"  # Merge tokens
        )

        logger.info("NER model loaded successfully")

    def _load_spacy_model(self):
        """Load SpaCy NER model"""
        logger.info("Loading SpaCy model: fr_core_news_lg")
        self.nlp = spacy.load("fr_core_news_lg")

    def extract_from_text(
        self,
        text: str,
        min_confidence: float = 0.7,
        context_window: int = 50
    ) -> List[Entity]:
        """
        Extract entities from text

        Args:
            text: Input text
            min_confidence: Minimum confidence threshold
            context_window: Characters of context around entity

        Returns:
            List of Entity objects
        """
        if self.use_spacy:
            return self._extract_spacy(text, context_window)
        else:
            return self._extract_transformer(text, min_confidence, context_window)

    def _extract_transformer(
        self,
        text: str,
        min_confidence: float,
        context_window: int
    ) -> List[Entity]:
        """Extract using transformer model"""
        # Run NER pipeline
        ner_results = self.ner_pipeline(text)

        entities = []
        for result in ner_results:
            # Filter by confidence
            if result['score'] < min_confidence:
                continue

            # Map entity type
            entity_type = self._map_entity_type(result['entity_group'])

            # Extract context
            start = max(0, result['start'] - context_window)
            end = min(len(text), result['end'] + context_window)
            context = text[start:end]

            entity = Entity(
                text=result['word'],
                type=entity_type,
                start=result['start'],
                end=result['end'],
                confidence=result['score'],
                context=context
            )
            entities.append(entity)

        return entities

    def _extract_spacy(self, text: str, context_window: int) -> List[Entity]:
        """Extract using SpaCy"""
        doc = self.nlp(text)

        entities = []
        for ent in doc.ents:
            entity_type = self._map_entity_type(ent.label_)

            # Extract context
            start_char = max(0, ent.start_char - context_window)
            end_char = min(len(text), ent.end_char + context_window)
            context = text[start_char:end_char]

            entity = Entity(
                text=ent.text,
                type=entity_type,
                start=ent.start_char,
                end=ent.end_char,
                confidence=1.0,  # SpaCy doesn't provide confidence
                context=context
            )
            entities.append(entity)

        return entities

    def _map_entity_type(self, label: str) -> EntityType:
        """Map model-specific labels to EntityType"""
        label_upper = label.upper()

        # Common mappings
        if 'PER' in label_upper or 'PERSON' in label_upper:
            return EntityType.PERSON
        elif 'LOC' in label_upper or 'GPE' in label_upper:
            return EntityType.LOCATION
        elif 'ORG' in label_upper:
            return EntityType.ORGANIZATION
        elif 'DATE' in label_upper:
            return EntityType.DATE
        elif 'TIME' in label_upper:
            return EntityType.TIME
        else:
            return EntityType.MISC

    def extract_from_conversation(
        self,
        turns: List[Dict[str, Any]],
        min_confidence: float = 0.7
    ) -> Dict[str, List[Entity]]:
        """
        Extract entities from all conversation turns

        Args:
            turns: List of conversation turns
            min_confidence: Minimum confidence

        Returns:
            Dict mapping turn index to list of entities
        """
        turn_entities = {}

        for idx, turn in enumerate(turns):
            text = turn.get('text', '')
            if not text:
                continue

            entities = self.extract_from_text(text, min_confidence)

            if entities:
                turn_entities[idx] = entities

        return turn_entities

    def aggregate_entities(
        self,
        turn_entities: Dict[str, List[Entity]]
    ) -> Dict[str, Set[str]]:
        """
        Aggregate and deduplicate entities across conversation

        Returns:
            Dict mapping entity type to set of unique entity texts
        """
        aggregated = {
            EntityType.PERSON: set(),
            EntityType.LOCATION: set(),
            EntityType.ORGANIZATION: set(),
            EntityType.DATE: set(),
            EntityType.TIME: set(),
            EntityType.MISC: set()
        }

        for entities in turn_entities.values():
            for entity in entities:
                # Normalize entity text
                normalized = entity.text.strip()
                aggregated[entity.type].add(normalized)

        # Convert sets to sorted lists for JSON serialization
        return {
            k.value: sorted(list(v))
            for k, v in aggregated.items()
            if v  # Only include non-empty
        }


class PersonExtractor:
    """
    Specialized extractor for person information
    Extracts names, roles, companies from conversations
    """

    def __init__(self, entity_extractor: EntityExtractor):
        self.entity_extractor = entity_extractor

    def extract_persons(
        self,
        turns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract person profiles from conversation

        Returns:
            List of person dicts with name, mentions, context
        """
        # Extract all entities
        turn_entities = self.entity_extractor.extract_from_conversation(turns)

        # Focus on persons
        persons = {}

        for turn_idx, entities in turn_entities.items():
            for entity in entities:
                if entity.type == EntityType.PERSON:
                    name = entity.text.strip()

                    if name not in persons:
                        persons[name] = {
                            'name': name,
                            'mentions': [],
                            'turns': [],
                            'confidence': []
                        }

                    persons[name]['mentions'].append({
                        'turn': turn_idx,
                        'context': entity.context,
                        'confidence': entity.confidence
                    })
                    persons[name]['turns'].append(turn_idx)
                    persons[name]['confidence'].append(entity.confidence)

        # Add statistics
        for name, data in persons.items():
            data['mention_count'] = len(data['mentions'])
            data['avg_confidence'] = sum(data['confidence']) / len(data['confidence'])
            data['first_mention_turn'] = min(data['turns'])
            data['last_mention_turn'] = max(data['turns'])

        return list(persons.values())


def extract_family_relations(
    turns: List[Dict[str, Any]],
    persons: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extract family relations from conversation
    Uses pattern matching for common family terms

    Returns:
        List of family relation dicts
    """
    import re

    relations = []
    family_patterns = {
        'spouse': r'(mari|femme|époux|épouse|conjoint)',
        'child': r'(fils|fille|enfant|garçon|bébé)',
        'parent': r'(père|mère|papa|maman|parent)',
        'sibling': r'(frère|sœur|soeur)',
        'grandparent': r'(grand-père|grand-mère|papi|mamie)',
        'grandchild': r'(petit-fils|petite-fille|petit-enfant)'
    }

    person_names = {p['name'] for p in persons}

    for turn in turns:
        text = turn.get('text', '').lower()

        for relation_type, pattern in family_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                # Look for person names near the family term
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]

                # Find person names in context
                for person_name in person_names:
                    if person_name.lower() in context:
                        relations.append({
                            'person': person_name,
                            'relation_type': relation_type,
                            'relation_term': match.group(0),
                            'context': context,
                            'turn': turn.get('turn', 0)
                        })

    return relations


if __name__ == "__main__":
    # Test NER
    logging.basicConfig(level=logging.INFO)

    extractor = EntityExtractor(
        model_name="camembert/camembert-ner",
        device="cuda"
    )

    test_text = "Jean-Pierre travaille chez Google à Paris depuis 2020."
    entities = extractor.extract_from_text(test_text)

    for entity in entities:
        print(f"{entity.type.value}: {entity.text} (confidence: {entity.confidence:.2f})")
