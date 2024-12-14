"""
测试报价单图片的物料匹配系统
"""
import asyncio
import os
import logging
from typing import List, Dict
import pandas as pd
from app.core.database import get_database, COLLECTIONS, close_database
from app.services.matcher.matcher import MaterialMatcher
from app.models.material import MaterialBase, MaterialMatch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_material_matching():
    """测试物料匹配系统"""
    try:
        # 初始化匹配器
        matcher = await MaterialMatcher.create()
        logger.info("物料匹配器初始化成功")

        # 获取测试图片
        test_images = get_test_images()
        logger.info(f"找到 {len(test_images)} 个测试图片")

        # 测试结果统计
        results = []
        total_matches = 0
        successful_matches = 0

        # 处理每个测试图片
        for image_path in test_images:
            logger.info(f"\n处理图片: {os.path.basename(image_path)}")

            # TODO: 这里先使用模拟数据，等OCR功能完成后替换
            # 模拟OCR识别结果
            test_items = [
                {"material_name": "不锈钢法兰", "specification": "DN50"},
                {"material_name": "碳钢法兰", "specification": "DN80"},
                {"material_name": "球阀", "specification": "DN100"}
            ]

            # 对每个识别项进行匹配
            for item in test_items:
                total_matches += 1
                match_result = await matcher.match_material(
                    item["material_name"],
                    item["specification"]
                )

                if match_result and match_result.confidence >= 0.7:
                    successful_matches += 1
                    results.append({
                        "图片": os.path.basename(image_path),
                        "识别名称": item["material_name"],
                        "识别规格": item["specification"],
                        "匹配物料编码": match_result.material_info.material_code,
                        "匹配物料名称": match_result.material_info.material_name,
                        "匹配规格": match_result.material_info.specification,
                        "匹配置信度": f"{match_result.confidence:.2%}",
                        "匹配状态": "成功"
                    })
                else:
                    results.append({
                        "图片": os.path.basename(image_path),
                        "识别名称": item["material_name"],
                        "识别规格": item["specification"],
                        "匹配物料编码": "",
                        "匹配物料名称": "",
                        "匹配规格": "",
                        "匹配置信度": "0%",
                        "匹配状态": "失败"
                    })

        # 生成测试报告
        if results:
            df = pd.DataFrame(results)
            report_path = "test_results/quotation_matching_report.xlsx"
            os.makedirs("test_results", exist_ok=True)
            df.to_excel(report_path, index=False)
            logger.info(f"\n测试报告已保存到: {report_path}")

        # 输出统计结果
        success_rate = (successful_matches / total_matches * 100) if total_matches > 0 else 0
        logger.info(f"\n测试统计:")
        logger.info(f"总匹配数: {total_matches}")
        logger.info(f"成功匹配: {successful_matches}")
        logger.info(f"匹配成功率: {success_rate:.2f}%")

    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        raise
    finally:
        await close_database()

def get_test_images() -> List[str]:
    """获取测试图片列表"""
    image_dir = os.path.expanduser("~/attachments")
    image_files = [
        f for f in os.listdir(image_dir)
        if f.startswith("WechatIMG") and f.endswith(".jpg")
    ]
    return [os.path.join(image_dir, f) for f in sorted(image_files)]

if __name__ == "__main__":
    asyncio.run(test_material_matching())
