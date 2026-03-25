"""
Setup configuration for ayugram-python SDK.

Ayugram Python SDK provides an async client for AyuGram JSON-RPC API
with PyTgCalls-compatible interface.
"""

from setuptools import setup, find_packages
import os


# Read version from __init__.py
def get_version():
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'ayugram', '__init__.py')) as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"').strip("'")
    raise RuntimeError('Unable to find version string.')


# Read README for long description
def get_long_description():
    here = os.path.abspath(os.path.dirname(__file__))
    readme_path = os.path.join(here, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return 'Ayugram Python SDK - Async client for AyuGram JSON-RPC API'


setup(
    name='ayugram-python',
    version=get_version(),
    author='Sattva Team',
    author_email='dev@sattva.io',
    description='Async Python client for AyuGram JSON-RPC API with PyTgCalls-compatible interface',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/sattva-ai/ayugram-python',
    project_urls={
        'Bug Reports': 'https://github.com/sattva-ai/ayugram-python/issues',
        'Source': 'https://github.com/sattva-ai/ayugram-python',
        'Documentation': 'https://github.com/sattva-ai/ayugram-python#readme',
    },
    packages=find_packages(exclude=['tests', 'tests.*', 'examples', 'examples.*']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Framework :: AsyncIO',
        'Typing :: Typed',
    ],
    python_requires='>=3.11',
    install_requires=[
        'aiohttp>=3.10.5',
        'pydantic>=2.9.2',
        'python-dotenv>=1.0.1',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.7.0',
            'ruff>=0.0.280',
            'isort>=5.12.0',
            'mypy>=1.5.0',
            'bandit>=1.7.5',
        ],
        'redis': [
            'redis>=5.0.1',
        ],
    },
    entry_points={
        'console_scripts': [
            # Add CLI commands here if needed in the future
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords='ayugram telegram json-rpc async voice-chat streaming pytgcalls',
)
