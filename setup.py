from setuptools import find_packages, setup


setup(
    name="ai-dev-team",
    version="0.1.0",
    description="Multi-agent AI software delivery orchestrator",
    packages=find_packages(include=["ai_dev_team", "ai_dev_team.*"]),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "openai",
        "pytest",
        "pydantic",
        "pydantic-settings",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "ai-dev-team=ai_dev_team.cli:main",
        ],
    },
    python_requires=">=3.10",
)
