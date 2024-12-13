import pytest
import asyncio
import logging
import motor.motor_asyncio
from app.core.config import settings
from app.core.database import Database

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope="session", autouse=True)
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
    client = None
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB]
        Database._db = db
        yield db
    finally:
        if client:
            await client.close()

@pytest.fixture(autouse=True)
async def clean_collections(database):
    """清理测试集合"""
    collections = ["materials", "ocr_tasks", "synonym_groups"]
    for collection in collections:
        await database[collection].delete_many({})
    yield
    for collection in collections:
        await database[collection].delete_many({})
