"""
本地物料匹配测试脚本
用于测试物料匹配系统的功能，不依赖OCR服务
"""
import asyncio
import os
import pandas as pd
from app.services.matcher.matcher import MaterialMatcher
from app.models.material import MaterialMatch
from app.core.config import settings
from app.core.database import get_database
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_material_matching():
    """测试物料匹配"""
    logger.info("开始物料匹配测试...")

    # 创建物料匹配器
    matcher = await MaterialMatcher.create()

    # 测试样例 - 基于实际数据的测试用例
    test_cases = [
        "首联湿式报警阀DN100",  # 完全匹配
        "湿式报警阀DN100",      # 部分匹配
        "不锈钢球阀DN50",       # 规格匹配
        "法兰盘DN100",          # 规格匹配
        "铜球阀",               # 类别匹配
        "蝶阀DN80",             # 规格匹配
        "首联雨淋报警阀DN100",  # 完全匹配
        "湿式阀门DN150",        # 模糊匹配
    ]

    print("\n=== 物料匹配测试结果 ===")
    print("=" * 50)

    for text in test_cases:
        logger.info(f"测试匹配: {text}")
        result = await matcher.match_material(text)

        print(f"\n输入文本: {text}")
        if result:
            print(f"匹配类型: {result.match_type}")
            print(f"匹配编码: {result.matched_code}")
            print(f"置信度: {result.confidence:.2f}")
            if result.material_info:
                print(f"物料名称: {result.material_info.material_name}")
                print(f"规格型号: {result.material_info.specification}")
                print(f"计量单位: {result.material_info.unit}")
                print(f"厂价: {result.material_info.factory_price}")
        else:
            print("未找到匹配")
        print("-" * 50)

    logger.info("物料匹配测试完成")

if __name__ == "__main__":
    asyncio.run(test_material_matching())
