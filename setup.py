from setuptools import setup, find_packages

setup(
    name="pricing-agent-ocr",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "alibabacloud-ocr-api20210707",
        "alibabacloud-tea-openapi",
        "alibabacloud-tea-util",
        "pydantic",
        "pydantic-settings",
        "python-dotenv",
        "pandas",
        "openpyxl",
        "oss2",
        "requests",
        "aiohttp",
    ],
) 