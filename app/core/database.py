from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    _client: AsyncIOMotorClient = None
    _db = None

    @classmethod
    async def init_db(cls, url: str, db_name: str):
        if cls._client is None:
            try:
                cls._client = AsyncIOMotorClient(url)
                cls._db = cls._client[db_name]
                logger.info(f"Connected to MongoDB: {url}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
                raise

    @classmethod
    def get_db(cls):
        if cls._db is None:
            raise RuntimeError("Database not initialized. Call init_db first.")
        return cls._db

    @classmethod
    async def close_db(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("Closed MongoDB connection")

COLLECTIONS = {
    "materials": "materials",
    "synonyms": "synonyms",
    "ocr_tasks": "ocr_tasks",
    "ocr_results": "ocr_results",
    "metrics": "performance_metrics"
}

async def create_indexes():
    db = Database.get_db()

    await db[COLLECTIONS["materials"]].create_index("material_code", unique=True)
    await db[COLLECTIONS["materials"]].create_index("material_name")

    await db[COLLECTIONS["synonyms"]].create_index("group_id", unique=True)
    await db[COLLECTIONS["synonyms"]].create_index("standard_name")
    await db[COLLECTIONS["synonyms"]].create_index("material_code")

    await db[COLLECTIONS["ocr_tasks"]].create_index("task_id", unique=True)
    await db[COLLECTIONS["ocr_tasks"]].create_index("created_at")
    await db[COLLECTIONS["ocr_tasks"]].create_index("status")

    await db[COLLECTIONS["ocr_results"]].create_index("created_at")

    await db[COLLECTIONS["metrics"]].create_index([
        ("timestamp", -1),
        ("operation", 1)
    ])
    await db[COLLECTIONS["metrics"]].create_index("operation")

    await db[COLLECTIONS["metrics"]].create_index(
        "timestamp",
        expireAfterSeconds=30 * 24 * 60 * 60
    )
