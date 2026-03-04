from setuptools import setup, find_packages

setup(
    name="canary-automation",
    version="1.0.0",
    description="A terminal-based tool for conducting simulated phishing campaigns and token auditing using CanaryTokens.",
    author="",
    author_email="",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "questionary>=2.0.1",
        "tqdm>=4.66.1",
        "tabulate>=0.9.0",
        "lxml>=5.1.0",
        "tenacity>=8.2.3",
        "rich>=13.0.0"
    ],
    entry_points={
        'console_scripts': [
            'canary-cmd=canary_automation:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
