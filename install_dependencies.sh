#!/bin/bash

# 安装基本依赖
pip install -r requirements.txt

# 安装PaddlePaddle (CPU版本，适用于Mac)
python -m pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple

# 安装PaddleOCR
pip install "paddleocr>=2.0.1" -i https://mirror.baidu.com/pypi/simple

# 下载中文OCR模型
paddleocr --download --lang ch