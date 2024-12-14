from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

COLLECTIONS = {
    "materials": "materials",
    "synonyms": "synonyms",
    "ocr_tasks": "ocr_tasks",
    "ocr_results": "ocr_results",
    "metrics": "performance_metrics"
}

_client: AsyncIOMotorClient = None
_db = None
_initialized = False

async def init_database():
    """Initialize database connection"""
    global _client, _db, _initialized
    try:
        if not _initialized:
            logger.info("Initializing MongoDB connection...")
            _client = AsyncIOMotorClient(settings.MONGODB_URL)
            _db = _client[settings.MONGODB_DB]
            # Test the connection
            await _db.command("ping")
            _initialized = True
            logger.info(f"Connected to MongoDB: {settings.MONGODB_URL}")
        return _db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        _client = None
        _db = None
        _initialized = False
        raise

async def get_database():
    """Get database instance, initializing if necessary"""
    global _db
    if not _initialized:
        await init_database()
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db

async def close_database():
    """Close database connection"""
    global _client, _db, _initialized
    try:
        if _client:
            _client.close()
        _client = None
        _db = None
        _initialized = False
        logger.info("Closed MongoDB connection")
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")

async def create_indexes():
    """Create database indexes"""
    db = await get_database()

    # Create material indexes
    await db[COLLECTIONS["materials"]].create_index("material_code", unique=True)
    await db[COLLECTIONS["materials"]].create_index("material_name")

    # Create synonym indexes
    await db[COLLECTIONS["synonyms"]].create_index("group_id", unique=True)
    await db[COLLECTIONS["synonyms"]].create_index("standard_name")
    await db[COLLECTIONS["synonyms"]].create_index("material_code")

    # Create OCR task indexes
    await db[COLLECTIONS["ocr_tasks"]].create_index("task_id", unique=True)
    await db[COLLECTIONS["ocr_tasks"]].create_index("created_at")
    await db[COLLECTIONS["ocr_tasks"]].create_index("status")

    # Create OCR results index
    await db[COLLECTIONS["ocr_results"]].create_index("created_at")

    # Create metrics indexes
    await db[COLLECTIONS["metrics"]].create_index([
        ("timestamp", -1),
        ("operation", 1)
    ])
    await db[COLLECTIONS["metrics"]].create_index("operation")
    await db[COLLECTIONS["metrics"]].create_index(
        "timestamp",
        expireAfterSeconds=30 * 24 * 60 * 60  # 30 days TTL
    )
