"""
清除数据库集合中的所有数据
"""
import asyncio
from app.core.database import get_database, COLLECTIONS

async def clear_collections():
    """清除materials和synonyms集合中的所有数据"""
    try:
        db = await get_database()
        await db[COLLECTIONS['materials']].delete_many({})
        await db[COLLECTIONS['synonyms']].delete_many({})
        print('数据库集合清除成功')
    except Exception as e:
        print(f'清除集合时出错: {str(e)}')

if __name__ == "__main__":
    asyncio.run(clear_collections())
