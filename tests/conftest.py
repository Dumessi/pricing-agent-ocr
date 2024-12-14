import os
import json
import pytest
import logging
import asyncio
from typing import Dict, List
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.database import init_database, close_database, COLLECTIONS
from app.models.material import MaterialBase, SynonymCreate
from app.services.matcher.synonym_service import SynonymService

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(name="test_db")
async def setup_test_database():
    """Setup test database"""
    try:
        # Use a test database
        os.environ["MONGODB_DB"] = "test_pricing_agent"
        os.environ["MONGODB_URL"] = "mongodb://localhost:27017"

        # Initialize database
        db = await init_database()
        logger.info("Initialized test database connection")

        # Clear all collections
        for collection in COLLECTIONS.values():
            await db[collection].delete_many({})
            logger.info(f"Cleaned collection: {collection}")

        # Load test materials data
        materials_data = [
            {
                "material_code": "M001",
                "material_name": "首联湿式报警阀DN100",
                "specification": "DN100",
                "unit": "台",
                "factory_price": 2000.0,
                "status": True,
                "category": "material_name"
            },
            {
                "material_code": "M002",
                "material_name": "球阀DN50",
                "specification": "DN50",
                "unit": "个",
                "factory_price": 150.0,
                "status": True,
                "category": "material_name"
            },
            {
                "material_code": "M003",
                "material_name": "闸阀2寸",
                "specification": "2寸",
                "unit": "台",
                "factory_price": 200.0,
                "status": True,
                "category": "material_name"
            },
            {
                "material_code": "M004",
                "material_name": "止回阀DN80",
                "specification": "DN80",
                "unit": "个",
                "factory_price": 180.0,
                "status": True,
                "category": "material_name"
            },
            {
                "material_code": "M005",
                "material_name": "蝶阀DN200",
                "specification": "DN200",
                "unit": "台",
                "factory_price": 300.0,
                "status": True,
                "category": "material_name"
            },
            {
                "material_code": "M006",
                "material_name": "法兰DN100",
                "specification": "DN100",
                "unit": "件",
                "factory_price": 80.0,
                "status": True,
                "category": "material_name"
            }
        ]

        # Insert materials with proper error handling
        try:
            result = await db[COLLECTIONS["materials"]].insert_many(materials_data)
            logger.info(f"Inserted {len(result.inserted_ids)} test materials")
        except Exception as e:
            logger.error(f"Error inserting materials: {str(e)}")
            raise

        # Create synonym groups with proper error handling
        synonym_service = await SynonymService.create()
        synonym_groups = [
            {
                "standard_name": "首联湿式报警阀DN100",
                "synonyms": ["湿式报警阀DN100", "ZSFZ-100", "湿式阀", "湿式阀DN100", "首联湿式阀DN100"],
                "material_code": "M001",
                "specification": "DN100",
                "unit": "台",
                "category": "material_name",
                "status": True
            },
            {
                "standard_name": "球阀DN50",
                "synonyms": ["不锈钢球阀DN50", "手动球阀DN50", "铜球阀DN50", "球阀DN50", "不锈钢球阀", "球阀"],
                "material_code": "M002",
                "specification": "DN50",
                "unit": "个",
                "category": "material_name",
                "status": True
            },
            {
                "standard_name": "闸阀2寸",
                "synonyms": ["闸阀2寸", "手动闸阀2寸", "铸铁闸阀2寸", "闸阀"],
                "material_code": "M003",
                "specification": "2寸",
                "unit": "台",
                "category": "material_name",
                "status": True
            },
            {
                "standard_name": "止回阀DN80",
                "synonyms": ["止回阀DN80", "单向阀DN80", "逆止阀DN80", "止回阀"],
                "material_code": "M004",
                "specification": "DN80",
                "unit": "个",
                "category": "material_name",
                "status": True
            },
            {
                "standard_name": "蝶阀DN200",
                "synonyms": ["蝶阀DN200", "手动蝶阀DN200", "对夹蝶阀DN200", "蝶阀"],
                "material_code": "M005",
                "specification": "DN200",
                "unit": "台",
                "category": "material_name",
                "status": True
            },
            {
                "standard_name": "法兰DN100",
                "synonyms": ["法兰盘", "法兰片", "平面法兰", "法兰"],
                "material_code": "M006",
                "specification": "DN100",
                "unit": "件",
                "category": "material_name",
                "status": True
            }
        ]

        for group in synonym_groups:
            try:
                await synonym_service.create_synonym_group(SynonymCreate(**group))
                logger.info(f"Created synonym group for: {group['standard_name']}")
            except Exception as e:
                logger.error(f"Error creating synonym group for {group['standard_name']}: {str(e)}")
                raise

        yield db

    except Exception as e:
        logger.error(f"Error setting up test database: {str(e)}")
        raise

    finally:
        # Cleanup
        await close_database()
        logger.info("Closed test database connection")
