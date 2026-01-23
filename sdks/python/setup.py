"""Setup configuration for sattva-api Python SDK."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sattva-api",
    version="0.1.0",
    author="Sattva",
    author_email="api@sattva.io",
    description="Official Python SDK for Sattva API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sattva/sattva-python-sdk",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
        ],
    },
    keywords="sattva api sdk streaming webhooks",
    project_urls={
        "Bug Reports": "https://github.com/sattva/sattva-python-sdk/issues",
        "Source": "https://github.com/sattva/sattva-python-sdk",
        "Documentation": "https://docs.sattva.io",
    },
)
