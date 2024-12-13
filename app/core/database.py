from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            print(f"Connected to MongoDB: {settings.MONGODB_URL}")
        return cls.client

    @classmethod
    def get_db(cls):
        if cls.db is None:
            cls.db = cls.get_client()[settings.MONGODB_DB]
        return cls.db

    @classmethod
    def close_connection(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("Closed MongoDB connection")

# 数据库集合名称
COLLECTIONS = {
    "materials": "materials",
    "synonyms": "synonyms",
    "ocr_tasks": "ocr_tasks",
    "ocr_results": "ocr_results",
    "metrics": "performance_metrics"
}

# 创建索引
async def create_indexes():
    db = Database.get_db()
    
    # 物料集合索引
    await db[COLLECTIONS["materials"]].create_index("material_code", unique=True)
    await db[COLLECTIONS["materials"]].create_index("material_name")
    
    # 同义词集合索引
    await db[COLLECTIONS["synonyms"]].create_index("group_id", unique=True)
    await db[COLLECTIONS["synonyms"]].create_index("standard_name")
    await db[COLLECTIONS["synonyms"]].create_index("material_code")
    
    # OCR任务集合索引
    await db[COLLECTIONS["ocr_tasks"]].create_index("task_id", unique=True)
    await db[COLLECTIONS["ocr_tasks"]].create_index("created_at")
    await db[COLLECTIONS["ocr_tasks"]].create_index("status")
    
    # OCR结果集合索引
    await db[COLLECTIONS["ocr_results"]].create_index("created_at")
    
    # 性能指标集合索引
    await db[COLLECTIONS["metrics"]].create_index([
        ("timestamp", -1),
        ("operation", 1)
    ])
    await db[COLLECTIONS["metrics"]].create_index("operation")
    
    # 设置性能指标集合的TTL索引（保留30天数据）
    await db[COLLECTIONS["metrics"]].create_index(
        "timestamp",
        expireAfterSeconds=30 * 24 * 60 * 60  # 30天
    )