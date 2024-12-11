from app.services.matcher.synonym_service import SynonymService
from app.core.database import Database, COLLECTIONS
from app.models.material import MaterialBase, SynonymCreate
import asyncio
import re

def generate_material_synonyms(material: MaterialBase) -> list:
    """生成物料名称的同义词"""
    synonyms = set()
    name = material.material_name
    
    # 1. 添加原始名称
    synonyms.add(name)
    
    # 2. 常见缩写和变体
    replacements = {
        "螺栓": ["螺丝", "螺丝钉"],
        "法兰": ["凸缘", "法兰盘"],
        "阀门": ["阀", "闸阀"],
        "管件": ["管配件", "配件"],
        "接头": ["连接头", "接口"],
        "密封": ["密封圈", "密封垫"],
        "垫片": ["垫圈", "密封垫"],
        "弯头": ["弯管", "弯"],
        "三通": ["T型管", "三叉"],
        "四通": ["十字管", "四叉"],
        "变径": ["异径", "大小头"],
        "补偿器": ["膨胀节", "伸缩节"],
        "过滤器": ["过滤", "滤"],
        "减压阀": ["减压器", "调压阀"],
        "截止阀": ["截止", "截流阀"],
        "球阀": ["球形阀", "球"],
        "蝶阀": ["蝶形阀", "蝶"],
        "止回阀": ["单向阀", "逆止阀"],
        "闸阀": ["闸门", "闸"],
        "电动": ["电动式", "电动型"],
        "手动": ["手动式", "手动型"],
        "气动": ["气动式", "气动型"],
        "液动": ["液动式", "液动型"]
    }
    
    # 处理替换
    for key, values in replacements.items():
        if key in name:
            for value in values:
                new_name = name.replace(key, value)
                synonyms.add(new_name)
    
    # 3. 处理品牌信息
    # 如果名称中包含括号，可能是品牌信息
    brand_match = re.search(r'\((.*?)\)', name)
    if brand_match:
        brand = brand_match.group(1)
        # 添加不带品牌的名称
        clean_name = name.replace(f"({brand})", "").strip()
        synonyms.add(clean_name)
        # 添加品牌在前面的变体
        synonyms.add(f"{brand}{clean_name}")
    
    # 4. 添加类别相关的同义词
    if material.category:
        if "level2" in material.category:
            category_name = material.category["level2"].replace("类", "")
            synonyms.add(f"{category_name}{name}")
    
    # 5. 添加材质相关的同义词
    if material.attributes and "material" in material.attributes:
        material_type = material.attributes["material"]
        synonyms.add(f"{material_type}{name}")
    
    return list(synonyms)

def generate_specification_synonyms(specification: str) -> list:
    """生成规格型号的同义词"""
    if not specification:
        return []
        
    synonyms = set()
    spec = specification.upper()
    
    # 1. 添加原始规格
    synonyms.add(spec)
    
    # 2. DN系列处理
    if spec.startswith("DN"):
        # 添加空格变体：DN100 -> DN 100
        synonyms.add(spec.replace("DN", "DN "))
        # 添加D变体：DN100 -> D100
        synonyms.add(spec.replace("DN", "D"))
        # 添加直径变体：DN100 -> Φ100
        synonyms.add(spec.replace("DN", "Φ"))
        # 添加数字变体：DN100 -> 100
        number = re.search(r'\d+', spec)
        if number:
            synonyms.add(number.group())
    
    # 3. 处理乘号变体
    if "*" in spec or "×" in spec or "X" in spec:
        variants = [
            spec.replace("*", "×"),
            spec.replace("*", "X"),
            spec.replace("×", "*"),
            spec.replace("×", "X"),
            spec.replace("X", "*"),
            spec.replace("X", "×")
        ]
        synonyms.update(variants)
    
    # 4. 处理带空格的变体
    if not " " in spec:
        # 在字母和数字之间添加空格
        spaced_spec = re.sub(r'([A-Za-z])(\d)', r'\1 \2', spec)
        if spaced_spec != spec:
            synonyms.add(spaced_spec)
    
    return list(synonyms)

async def generate_all_synonyms():
    """为所有物料生成同义词"""
    db = Database.get_db()
    materials_collection = db[COLLECTIONS["materials"]]
    synonym_service = SynonymService()
    
    # 获取所有物料
    cursor = materials_collection.find({"status": True})
    
    # 统计计数器
    total_count = 0
    success_count = 0
    error_count = 0
    
    async for doc in cursor:
        total_count += 1
        material = MaterialBase(**doc)
        
        try:
            # 1. 生成物料名称同义词
            name_synonyms = generate_material_synonyms(material)
            if name_synonyms:
                name_group = SynonymCreate(
                    standard_name=material.material_name,
                    synonyms=name_synonyms,
                    material_code=material.material_code,
                    category="material_name"
                )
                await synonym_service.create_synonym_group(name_group)
            
            # 2. 生成规格型号同义词
            if material.specification:
                spec_synonyms = generate_specification_synonyms(material.specification)
                if spec_synonyms:
                    spec_group = SynonymCreate(
                        standard_name=material.specification,
                        synonyms=spec_synonyms,
                        material_code=material.material_code,
                        category="specification"
                    )
                    await synonym_service.create_synonym_group(spec_group)
            
            success_count += 1
            
            # 每100条打印一次进度
            if total_count % 100 == 0:
                print(f"Processed {total_count} materials, {success_count} successful, {error_count} failed")
                
        except Exception as e:
            error_count += 1
            print(f"Error processing material {material.material_code}: {str(e)}")
    
    print(f"\nFinished processing {total_count} materials:")
    print(f"Successful: {success_count}")
    print(f"Failed: {error_count}")

if __name__ == "__main__":
    asyncio.run(generate_all_synonyms()) 