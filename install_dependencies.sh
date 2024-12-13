#!/bin/bash

# 安装基本依赖
pip install -r requirements.txt

# 安装PaddlePaddle (CPU版本，适用于Mac)
python -m pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple

# 安装PaddleOCR
pip install "paddleocr>=2.0.1" -i https://mirror.baidu.com/pypi/simple

# 安装OpenCV
pip install "opencv-python>=4.8.0" "opencv-python-headless>=4.8.0"

# 下载中文OCR模型
paddleocr --download --lang ch

# 创建必要的目录
mkdir -p uploads
mkdir -p inference