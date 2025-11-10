"""Setup script for wear CLI tool."""

from setuptools import setup

setup(
    name="synheart-wear-cli",
    version="0.1.0",
    description="Synheart Wear CLI - Cloud wearable integration tool",
    author="Synheart",
    author_email="opensource@synheart.ai",
    py_modules=["wear"],
    install_requires=[
        "typer[all]>=0.9.0",
        "rich>=13.0.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
        "pyngrok>=7.0.0",
        # Dependencies from py-cloud-connector (required for tokens/connector commands)
        "pydantic>=2.0.0",
        "boto3>=1.34.0",
        "cryptography>=42.0.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "wear=wear:app",
        ],
    },
    python_requires=">=3.11",
)
