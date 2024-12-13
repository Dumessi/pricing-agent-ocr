```python
from alibabacloud_ocr20191230 import models as ocr_models
import inspect

def inspect_recognize_table_request():
    # Get the signature of RecognizeTableRequest
    sig = inspect.signature(ocr_models.RecognizeTableRequest.__init__)

    # Print all parameters and their details
    print("RecognizeTableRequest parameters:")
    for param_name, param in sig.parameters.items():
        if param_name != 'self':
            print(f"- {param_name}: {param.default if param.default != inspect._empty else 'Required'}")

if __name__ == '__main__':
    inspect_recognize_table_request()
```
