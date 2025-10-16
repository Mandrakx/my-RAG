"""
Configuration for ingestion pipeline
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class IngestionConfig(BaseSettings):
    """Ingestion pipeline configuration"""

    # MinIO Configuration
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ROOT_USER")
    minio_secret_key: str = Field(default="minioadmin", env="MINIO_ROOT_PASSWORD")
    minio_secure: bool = Field(default=False, env="MINIO_USE_SSL")
    minio_region: str = Field(default="us-east-1", env="MINIO_REGION")

    # MinIO Buckets
    minio_bucket_ingestion: str = Field(default="ingestion", env="MINIO_BUCKET_INGESTION")
    minio_bucket_results: str = Field(default="results", env="MINIO_BUCKET_RESULTS")
    minio_bucket_archive: str = Field(default="archive", env="MINIO_BUCKET_ARCHIVE")

    # Redis Configuration (aligned with ADR-2025-10-03-003)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_stream_name: str = Field(default="audio.ingestion", env="REDIS_STREAM_INGESTION")
    redis_consumer_group: str = Field(default="rag-ingestion", env="REDIS_CONSUMER_GROUP")
    redis_consumer_name: str = Field(default="consumer-1", env="REDIS_CONSUMER_NAME")
    redis_dlq_stream: str = Field(default="audio.ingestion.deadletter", env="REDIS_DLQ_STREAM")
    redis_max_retries: int = Field(default=3, env="REDIS_MAX_RETRIES")
    redis_block_ms: int = Field(default=5000, env="REDIS_BLOCK_MS")  # 5 seconds
    redis_batch_size: int = Field(default=10, env="REDIS_BATCH_SIZE")

    # PostgreSQL Configuration
    database_url: str = Field(env="DATABASE_URL")

    # Qdrant Configuration
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="conversations", env="QDRANT_COLLECTION_NAME")

    # Processing Configuration
    max_file_size_mb: int = Field(default=500, env="MAX_FILE_SIZE_MB")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")

    # Embedding Configuration
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, env="EMBEDDING_DIMENSION")

    # Retry Configuration
    max_retries: int = Field(default=3, env="INGESTION_MAX_RETRIES")
    retry_delay_seconds: int = Field(default=5, env="INGESTION_RETRY_DELAY")
    retry_backoff_factor: float = Field(default=2.0, env="INGESTION_RETRY_BACKOFF")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


class ServiceClients:
    """Singleton for service clients"""
    _instance = None
    _minio_client = None
    _redis_client = None
    _db_session = None
    _qdrant_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceClients, cls).__new__(cls)
        return cls._instance

    @property
    def minio(self):
        """Get MinIO client"""
        if self._minio_client is None:
            from minio import Minio
            config = IngestionConfig()
            self._minio_client = Minio(
                config.minio_endpoint,
                access_key=config.minio_access_key,
                secret_key=config.minio_secret_key,
                secure=config.minio_secure,
                region=config.minio_region
            )
        return self._minio_client

    @property
    def redis(self):
        """Get Redis client"""
        if self._redis_client is None:
            import redis
            config = IngestionConfig()
            self._redis_client = redis.from_url(config.redis_url)
        return self._redis_client

    @property
    def qdrant(self):
        """Get Qdrant client"""
        if self._qdrant_client is None:
            from qdrant_client import QdrantClient
            config = IngestionConfig()
            self._qdrant_client = QdrantClient(
                url=config.qdrant_url,
                api_key=config.qdrant_api_key
            )
        return self._qdrant_client

    def get_db_session(self):
        """Get database session"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        config = IngestionConfig()

        if self._db_session is None:
            engine = create_engine(config.database_url)
            Session = sessionmaker(bind=engine)
            self._db_session = Session()

        return self._db_session

    def close_all(self):
        """Close all connections"""
        if self._db_session:
            self._db_session.close()
            self._db_session = None

        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None

        # MinIO and Qdrant clients don't need explicit closing
        self._minio_client = None
        self._qdrant_client = None


# Global instance
clients = ServiceClients()
