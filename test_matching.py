from app.services.matcher.matcher import MaterialMatcher
import asyncio

async def test_matching():
    matcher = MaterialMatcher()
    
    # 测试用例
    test_cases = [
        # 完全匹配测试
        "首联湿式报警阀DN100",
        # 同义词匹配测试
        "湿式报警阀",
        "报警阀门",
        # 规格匹配测试
        "球阀 DN100",
        "法兰 d100",
        # 模糊匹配测试
        "不锈钢法兰盘",
        "铸铁闸阀",
        # 复杂情况测试
        "DN100 球形阀门",
        "100mm 球阀",
        "1寸球阀"
    ]
    
    print("=== 匹配测试结果 ===")
    for text in test_cases:
        print(f"\n测试文本: {text}")
        result = await matcher.match_material(text)
        print(f"匹配类型: {result.match_type}")
        print(f"置信度: {result.confidence}")
        print(f"匹配编码: {result.matched_code}")
        if result.material_info:
            print(f"物料名称: {result.material_info.material_name}")
            print(f"规格型号: {result.material_info.specification}")

if __name__ == "__main__":
    asyncio.run(test_matching()) 