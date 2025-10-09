"""
Unit tests for entity extraction module
"""

import pytest
from datetime import datetime
from src.rag.entity_extraction import GPUEntityExtractor, PersonInfo, ConversationEntities

class TestGPUEntityExtractor:
    """Test cases for GPU entity extractor"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        return GPUEntityExtractor(device="cpu")  # Use CPU for testing

    @pytest.fixture
    def sample_conversation(self):
        """Sample conversation text for testing"""
        return """
        Hier j'ai eu une réunion avec Jean Dupont, le directeur commercial chez Acme Corp.
        Nous avons discuté du projet Alpha qui doit être livré le 15 mars 2025.
        Jean m'a parlé de sa fille Sophie qui a 8 ans et de son fils Thomas qui fête ses 12 ans
        le 25 avril. Sa femme Marie travaille également dans le secteur technologique.

        Nous nous sommes rencontrés au café de la place République à Paris.
        Jean semble inquiet par les délais du projet mais reste optimiste pour la suite.

        Actions à faire:
        - Envoyer la proposition commerciale avant vendredi
        - Organiser une réunion avec l'équipe technique
        - Suivre l'avancement du développement
        """

    def test_extract_persons(self, extractor, sample_conversation):
        """Test person extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.persons) > 0

        # Find Jean Dupont
        jean = next((p for p in entities.persons if "Jean" in p.name), None)
        assert jean is not None
        assert jean.role is not None
        assert "commercial" in jean.role.lower() or "directeur" in jean.role.lower()

    def test_extract_family_relations(self, extractor, sample_conversation):
        """Test family relationship extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        # Should find family members
        jean = next((p for p in entities.persons if "Jean" in p.name), None)
        if jean:
            assert len(jean.family_members) > 0
            # Should find wife and children
            family_relations = list(jean.family_members.keys())
            assert any("children" in rel or "fils" in rel or "fille" in rel for rel in family_relations)

    def test_extract_dates(self, extractor, sample_conversation):
        """Test date extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.dates) > 0

        # Should find project deadline
        project_date = next((d for d in entities.dates if "15 mars" in d.get('original_text', '')), None)
        assert project_date is not None

    def test_extract_organizations(self, extractor, sample_conversation):
        """Test organization extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.organizations) > 0
        assert any("Acme" in org for org in entities.organizations)

    def test_extract_projects(self, extractor, sample_conversation):
        """Test project extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.projects) > 0
        assert any("Alpha" in project for project in entities.projects)

    def test_extract_action_items(self, extractor, sample_conversation):
        """Test action item extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.action_items) > 0
        # Should find at least one action
        assert any("proposition" in action.lower() for action in entities.action_items)

    def test_extract_locations(self, extractor, sample_conversation):
        """Test location extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.locations) > 0
        # Should find Paris
        assert any("Paris" in loc.get('name', '') for loc in entities.locations)

    def test_sentiment_analysis(self, extractor, sample_conversation):
        """Test sentiment moment extraction"""
        entities = extractor.extract_all_entities(sample_conversation)

        assert len(entities.sentiment_moments) > 0

        # Should detect both negative (inquiet) and positive (optimiste) sentiments
        sentiments = [s['sentiment'] for s in entities.sentiment_moments]
        assert 'negative' in sentiments or 'positive' in sentiments

    def test_gps_extraction(self, extractor):
        """Test GPS coordinate extraction"""
        text = "Nous nous sommes rencontrés au bureau situé aux coordonnées 48.8566, 2.3522"
        entities = extractor.extract_all_entities(text)

        # Should find GPS coordinates
        gps_location = next((loc for loc in entities.locations if 'gps' in loc), None)
        if gps_location:
            assert gps_location['gps']['latitude'] == 48.8566
            assert gps_location['gps']['longitude'] == 2.3522

    def test_birthday_extraction(self, extractor):
        """Test birthday extraction"""
        text = "L'anniversaire de Marie est le 15 juin"
        entities = extractor.extract_all_entities(text)

        # Should classify as birthday
        birthday_date = next((d for d in entities.dates if d.get('type') == 'birthday'), None)
        assert birthday_date is not None

    def test_batch_processing(self, extractor):
        """Test batch processing capability"""
        texts = [
            "Réunion avec Paul Martin demain",
            "Anniversaire de Sophie le 10 mai",
            "Projet Beta en cours chez TechCorp"
        ]

        results = extractor.batch_extract(texts, batch_size=2)

        assert len(results) == 3
        assert all(isinstance(r, ConversationEntities) for r in results)

    def test_personal_info_extraction(self, extractor):
        """Test personal information extraction"""
        text = """
        Marie adore le tennis et la lecture. Elle fait du yoga tous les matins.
        Son hobby principal est la photographie. Elle n'aime pas les films d'horreur.
        Son objectif est de devenir chef de projet d'ici 2 ans.
        """

        entities = extractor.extract_all_entities(text)
        personal_info = entities.personal_info

        assert len(personal_info.get('hobbies', [])) > 0
        # Should find hobbies like tennis, lecture, yoga, photographie


class TestDateExtractor:
    """Test cases for date extraction"""

    def test_relative_dates(self):
        """Test relative date parsing"""
        from src.rag.entity_extraction.entity_extractor import DateExtractor

        extractor = DateExtractor()
        base_date = datetime(2025, 1, 22, 14, 30)

        text = "Réunion demain à 14h et après-demain en fin de journée"
        dates = extractor.extract(text, base_date)

        assert len(dates) >= 1
        # Should parse relative dates correctly

    def test_written_dates(self):
        """Test written date formats"""
        from src.rag.entity_extraction.entity_extractor import DateExtractor

        extractor = DateExtractor()
        text = "Le 15 janvier 2025 nous aurons une présentation"
        dates = extractor.extract(text)

        assert len(dates) >= 1
        parsed_date = dates[0]['parsed']
        assert parsed_date.day == 15
        assert parsed_date.month == 1
        assert parsed_date.year == 2025


class TestLocationExtractor:
    """Test cases for location extraction"""

    def test_gps_extraction(self):
        """Test GPS coordinate extraction"""
        from src.rag.entity_extraction.entity_extractor import LocationExtractor

        extractor = LocationExtractor()
        text = "Rendez-vous aux coordonnées 48.8566, 2.3522"
        locations = extractor.extract(text)

        assert len(locations) >= 1
        gps_location = next((loc for loc in locations if loc['type'] == 'gps'), None)
        assert gps_location is not None
        assert gps_location['coordinates']['latitude'] == 48.8566


class TestRelationshipExtractor:
    """Test cases for relationship extraction"""

    def test_professional_relationships(self):
        """Test professional relationship extraction"""
        from src.rag.entity_extraction.entity_extractor import RelationshipExtractor

        extractor = RelationshipExtractor()
        text = "Paul manage l'équipe de Marie. Sophie travaille avec Jean."
        relationships = extractor.extract(text)

        assert len(relationships) >= 1
        # Should find management and collaboration relationships

    def test_family_relationships(self):
        """Test family relationship extraction"""
        from src.rag.entity_extraction.entity_extractor import RelationshipExtractor

        extractor = RelationshipExtractor()
        text = "Marie est mariée à Paul"
        relationships = extractor.extract(text)

        married_relationship = next((rel for rel in relationships if rel['type'] == 'married_to'), None)
        assert married_relationship is not None


if __name__ == "__main__":
    pytest.main([__file__])