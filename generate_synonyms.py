from app.services.matcher.synonym_service import SynonymService
from app.core.database import get_database, COLLECTIONS
from app.models.material import MaterialBase, SynonymCreate
import asyncio
import re

def generate_material_synonyms(material: MaterialBase) -> list:
    """生成物料名称的同义词"""
    synonyms = set()
    name = material.material_name

    # 1. 添加原始名称
    synonyms.add(name)

    # 2. 常见材质前缀
    material_types = {
        "不锈钢": ["SS", "304", "316", "316L", "不锈"],
        "碳钢": ["CS", "Q235", "20#", "碳"],
        "铸铁": ["Cast Iron", "铸"],
        "铜": ["Copper", "紫铜", "黄铜"],
        "铝": ["AL", "铝合金"],
        "塑料": ["PP", "PE", "PVC", "塑"]
    }

    # 3. 常见缩写和变体
    replacements = {
        "螺栓": ["螺丝", "螺丝钉", "bolt"],
        "法兰": ["凸缘", "法兰盘", "flange"],
        "阀门": ["阀", "闸阀", "valve"],
        "管件": ["管配件", "配件", "fitting"],
        "接头": ["连接头", "接口", "connector"],
        "密封": ["密封圈", "密封垫", "seal"],
        "垫片": ["垫圈", "密封垫", "gasket"],
        "弯头": ["弯管", "弯", "elbow"],
        "三通": ["T型管", "三叉", "tee"],
        "四通": ["十字管", "四叉", "cross"],
        "变径": ["异径", "大小头", "reducer"],
        "补偿器": ["膨胀节", "伸缩节", "compensator"],
        "过滤器": ["过滤", "滤", "filter"],
        "减压阀": ["减压器", "调压阀", "PRV"],
        "截止阀": ["截止", "截流阀", "stop valve"],
        "球阀": ["球形阀", "球", "ball valve"],
        "蝶阀": ["蝶形阀", "蝶", "butterfly valve"],
        "止回阀": ["单向阀", "逆止阀", "check valve"],
        "闸阀": ["闸门", "闸", "gate valve"],
        "电动": ["电动式", "电动型", "electric"],
        "手动": ["手动式", "手动型", "manual"],
        "气动": ["气动式", "气动型", "pneumatic"],
        "液动": ["液动式", "液动型", "hydraulic"]
    }

    # 处理材质前缀
    base_name = name
    current_type = None
    for mat_type, variants in material_types.items():
        if any(variant in name for variant in [mat_type] + variants):
            current_type = mat_type
            # 移除材质前缀得到基础名称
            for variant in [mat_type] + variants:
                if variant in name:
                    base_name = name.replace(variant, "").strip()
                    break
            break

    # 处理替换
    for key, values in replacements.items():
        if key in base_name:
            # 添加基础替换
            for value in values:
                new_name = base_name.replace(key, value)
                synonyms.add(new_name)
                # 如果有材质，添加带材质的变体
                if current_type:
                    synonyms.add(f"{current_type}{new_name}")
                    for mat_variant in material_types.get(current_type, []):
                        synonyms.add(f"{mat_variant}{new_name}")

    # 添加不带材质前缀的基础名称
    if current_type and base_name != name:
        synonyms.add(base_name)

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
    dn_pattern = re.compile(r'DN\s*(\d+)', re.IGNORECASE)
    dn_match = dn_pattern.search(spec)
    if dn_match:
        size = dn_match.group(1)
        # 添加各种DN变体
        dn_variants = [
            f"DN{size}",
            f"DN {size}",
            f"D{size}",
            f"D {size}",
            f"Φ{size}",
            f"Φ {size}",
            size,
            f"{size}mm",
            f"公称直径{size}",
            f"直径{size}"
        ]
        synonyms.update(dn_variants)

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
    if " " not in spec:
        # 在字母和数字之间添加空格
        spaced_spec = re.sub(r'([A-Za-z])(\d)', r'\1 \2', spec)
        if spaced_spec != spec:
            synonyms.add(spaced_spec)

    return list(synonyms)

async def generate_all_synonyms():
    """为所有物料生成同义词"""
    print("初始化数据库连接...")
    db = await get_database()
    materials_collection = db[COLLECTIONS["materials"]]
    synonyms_collection = db[COLLECTIONS["synonyms"]]

    print("初始化同义词服务...")
    synonym_service = await SynonymService.create()

    print("清除现有同义词...")
    await synonyms_collection.delete_many({})

    print("获取所有物料...")
    cursor = materials_collection.find({})

    # 统计计数器
    total_count = 0
    success_count = 0
    error_count = 0

    async for material in cursor:
        total_count += 1
        try:
            print(f"\n处理物料: {material.get('material_code', 'UNKNOWN')}")
            print(f"物料数据: {material}")

            material_obj = MaterialBase(**material)
            print(f"转换为MaterialBase对象: {material_obj}")

            # 生成物料名称同义词
            name_synonyms = generate_material_synonyms(material_obj)
            if name_synonyms:
                print(f"生成名称同义词: {name_synonyms}")
                name_group = SynonymCreate(
                    standard_name=material_obj.material_name,
                    synonyms=name_synonyms,
                    material_code=material_obj.material_code,
                    specification=material_obj.specification,
                    unit=material_obj.unit,
                    factory_price=material_obj.factory_price,
                    category="material_name"
                )
                print(f"创建同义词组: {name_group}")
                try:
                    result = await synonym_service.create_synonym_group(name_group)
                    print(f"保存同义词组结果: {result}")
                except Exception as e:
                    print(f"保存同义词组失败: {str(e)}")
                    print(f"错误类型: {type(e)}")
                    raise e

            # 生成规格同义词
            if material_obj.specification:
                spec_synonyms = generate_specification_synonyms(material_obj.specification)
                if spec_synonyms:
                    print(f"生成规格同义词: {spec_synonyms}")
                    spec_group = SynonymCreate(
                        standard_name=material_obj.specification,
                        synonyms=spec_synonyms,
                        material_code=material_obj.material_code,
                        specification=material_obj.specification,
                        unit=material_obj.unit,
                        factory_price=material_obj.factory_price,
                        category="specification"
                    )
                    print(f"创建规格同义词组: {spec_group}")
                    try:
                        result = await synonym_service.create_synonym_group(spec_group)
                        print(f"保存规格同义词组结果: {result}")
                    except Exception as e:
                        print(f"保存规格同义词组失败: {str(e)}")
                        print(f"错误类型: {type(e)}")
                        raise e

            success_count += 1

            if total_count % 100 == 0:
                print(f"\n已处理 {total_count} 个物料, {success_count} 个成功, {error_count} 个失败")

        except Exception as e:
            error_count += 1
            print(f"处理物料 {material.get('material_code', 'UNKNOWN') } 时出错: {str(e)}")
            print(f"错误类型: {type(e)}")
            continue

    print(f"\n处理完成，共处理 {total_count} 个物料:")
    print(f"成功: {success_count}")
    print(f"失败: {error_count}")

if __name__ == "__main__":
    asyncio.run(generate_all_synonyms()) 