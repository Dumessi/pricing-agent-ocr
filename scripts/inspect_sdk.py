from alibabacloud_ocr20191230 import models as ocr_models
import inspect

def inspect_sdk():
    """检查SDK模型的结构"""
    # 检查RecognizeTableRequest的结构
    print("=== RecognizeTableRequest 类结构 ===")
    print(inspect.getfullargspec(ocr_models.RecognizeTableRequest))

    # 创建一个示例请求对象并检查其属性
    request = ocr_models.RecognizeTableRequest()
    print("\n=== RecognizeTableRequest 实例属性 ===")
    print(dir(request))

if __name__ == "__main__":
    inspect_sdk()
