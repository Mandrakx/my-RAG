"""
Database initialization script
Creates tables for ingestion pipeline
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingestion.models import Base, IngestionJob, Conversation, ConversationTurn
from src.ingestion.config import IngestionConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with all tables"""
    config = IngestionConfig()

    logger.info(f"Connecting to database: {config.database_url.split('@')[-1]}")  # Hide credentials

    # Create engine
    engine = create_engine(config.database_url)

    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)

    logger.info("Database initialization complete!")

    # List created tables
    logger.info(f"Created tables: {', '.join(Base.metadata.tables.keys())}")


def drop_all_tables():
    """Drop all tables (use with caution!)"""
    config = IngestionConfig()
    engine = create_engine(config.database_url)

    logger.warning("Dropping all tables...")
    Base.metadata.drop_all(engine)
    logger.info("All tables dropped")


def reset_database():
    """Reset database (drop and recreate)"""
    logger.warning("Resetting database...")
    drop_all_tables()
    init_database()
    logger.info("Database reset complete")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            init_database()
        elif command == "drop":
            response = input("Are you sure you want to drop all tables? (yes/no): ")
            if response.lower() == "yes":
                drop_all_tables()
            else:
                logger.info("Operation cancelled")
        elif command == "reset":
            response = input("Are you sure you want to reset the database? (yes/no): ")
            if response.lower() == "yes":
                reset_database()
            else:
                logger.info("Operation cancelled")
        else:
            print(f"Unknown command: {command}")
            print("Usage: python init_db.py [init|drop|reset]")
    else:
        init_database()
