"""
MongoDB Database Configuration and Connection
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

client: Optional[AsyncIOMotorClient] = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB and ensure indexes are in place."""
    global client, database
    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("MONGODB_DATABASE", "ai_resume_analyzer")
    mongodb_required = os.getenv("MONGODB_REQUIRED", "false").lower() == "true"

    if not mongodb_url:
        msg = "MONGODB_URL is not set. Running in demo mode without persistent storage."
        if mongodb_required:
            raise RuntimeError("MONGODB_URL is required but not configured")
        logger.warning(msg)
        logger.warning("Auth and data storage features will be limited.")
        return

    try:
        client = AsyncIOMotorClient(
            mongodb_url,
            server_api=ServerApi('1'),
            maxPoolSize=int(os.getenv("MONGODB_MAX_POOL_SIZE", "20")),
            minPoolSize=1,
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000,
        )

        await client.admin.command("ping")
        database = client[database_name]

        await _ensure_indexes()

        logger.info("Connected to MongoDB (database=%s)", database_name)

    except Exception as e:
        if mongodb_required:
            raise RuntimeError(f"MongoDB connection failed: {str(e)}") from e
        logger.warning("MongoDB connection failed: %s", str(e))
        logger.info("Running in demo mode - matching engine is available")
        logger.info("To enable data persistence, configure a valid MONGODB_URL")


async def _ensure_indexes() -> None:
    """Create indexes for efficient queries (idempotent)."""
    if database is None:
        return
    try:
        await database.users.create_index("email", unique=True)
        await database.resumes.create_index([("user_id", 1), ("uploaded_at", -1)])
        await database.job_descriptions.create_index([("user_id", 1), ("created_at", -1)])
        await database.analysis_results.create_index([("user_id", 1), ("created_at", -1)])
        await database.analysis_results.create_index("resume_id")
        await database.user_profiles.create_index("user_id", unique=True)
        # Password reset records: lookup by email + auto-expire when expires_at passes
        await database.password_resets.create_index("email")
        await database.password_resets.create_index("expires_at", expireAfterSeconds=0)
        logger.info("MongoDB indexes ensured")
    except Exception as exc:
        logger.warning("Index creation skipped: %s", exc)


async def close_mongo_connection():
    """
    Close MongoDB connection
    """
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")


def get_database():
    """
    Get database instance
    """
    return database


def get_users_collection():
    """Get users collection"""
    if database is None:
        return None
    return database.users


def get_resumes_collection():
    """Get resumes collection"""
    if database is None:
        return None
    return database.resumes


def get_job_descriptions_collection():
    """Get job descriptions collection"""
    if database is None:
        return None
    return database.job_descriptions


def get_analysis_results_collection():
    """Get analysis results collection"""
    if database is None:
        return None
    return database.analysis_results


def get_user_profiles_collection():
    """Get user_profiles collection (one resume profile per user)."""
    if database is None:
        return None
    return database.user_profiles


def get_password_resets_collection():
    """Get password_resets collection (OTP records for forgot-password flow)."""
    if database is None:
        return None
    return database.password_resets
