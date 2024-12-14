import time
from functools import wraps
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.database import get_database, COLLECTIONS
import logging

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    def __init__(self):
        self.db = None
        self.collection = None

    @classmethod
    async def create(cls) -> 'PerformanceMetrics':
        """Factory method to create a new PerformanceMetrics instance"""
        metrics = cls()
        metrics.db = await get_database()
        metrics.collection = metrics.db[COLLECTIONS.get("metrics", "performance_metrics")]
        return metrics

    async def record_metric(self,
                          operation: str,
                          duration: float,
                          success: bool,
                          details: Optional[Dict] = None):
        """记录性能指标"""
        metric = {
            "timestamp": datetime.utcnow(),
            "operation": operation,
            "duration": duration,
            "success": success,
            "details": details or {}
        }
        await self.collection.insert_one(metric)

    async def get_metrics(self,
                         operation: Optional[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[Dict]:
        """获取性能指标"""
        query = {}
        if operation:
            query["operation"] = operation
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time

        cursor = self.collection.find(query)
        return [doc async for doc in cursor]

    async def get_average_duration(self, operation: str) -> float:
        """获取操作的平均耗时"""
        pipeline = [
            {"$match": {"operation": operation}},
            {"$group": {
                "_id": None,
                "avg_duration": {"$avg": "$duration"}
            }}
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        return result[0]["avg_duration"] if result else 0

    async def get_success_rate(self, operation: str) -> float:
        """获取操作的成功率"""
        pipeline = [
            {"$match": {"operation": operation}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "success_count": {
                    "$sum": {"$cond": ["$success", 1, 0]}
                }
            }}
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        if not result:
            return 0
        return result[0]["success_count"] / result[0]["total"]

def monitor_performance(operation: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = await PerformanceMetrics.create()  # Properly await the async initialization
            start_time = time.time()
            success = True
            details = {}

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                details["error"] = str(e)
                raise
            finally:
                duration = time.time() - start_time
                await metrics.record_metric(
                    operation=operation,
                    duration=duration,
                    success=success,
                    details=details
                )
        return wrapper
    return decorator 