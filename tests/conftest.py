import pytest
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.database import Database, COLLECTIONS

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def database():
    """创建数据库连接"""
    try:
        await Database.init_db(settings.MONGODB_URL, settings.MONGODB_DB)
        logger.info("Test database initialized")
        yield Database.get_db()
    finally:
        if Database._client:
            await Database.close_db()
            logger.info("Test database connection closed")

@pytest.fixture(autouse=True)
async def clean_collections(database):
    """清理测试集合"""
    for collection_name in COLLECTIONS.values():
        await database[collection_name].delete_many({})
        logger.info(f"Cleaned collection: {collection_name}")
    yield
    for collection_name in COLLECTIONS.values():
        await database[collection_name].delete_many({})
        logger.info(f"Cleaned collection: {collection_name}")
