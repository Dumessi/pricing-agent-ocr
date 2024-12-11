from setuptools import setup, find_packages

setup(
    name="pricing-agent-ocr",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-multipart==0.0.6",
        "pandas",
        "openpyxl==3.1.2",
        "Pillow",
        "pymongo==4.6.0",
        "python-dotenv==1.0.0",
        "pydantic==2.5.1",
        "numpy==1.26.2",
        "scikit-learn==1.3.2",
        "motor==3.3.1",
        "pydantic-settings==2.1.0",
        "python-Levenshtein",
        "rapidfuzz"
    ],
) 