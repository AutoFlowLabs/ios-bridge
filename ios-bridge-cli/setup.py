from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="ios-bridge-cli",
    version="1.0.0",
    description="Desktop streaming client for iOS Bridge simulator sessions",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="iOS Bridge Team",
    author_email="kukreja.him@gmail.com",
    url="https://github.com/AutoFlowLabs/ios-bridge-cli",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'ios_bridge_cli': [
            'electron_app/**/*',
            'electron_app/src/**/*',
            'electron_app/dist/**/*',
        ],
    },
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "websockets>=10.0",
        "pillow>=8.0.0",
        "psutil>=5.8.0",
        "aiohttp>=3.8.0",
    ],
    entry_points={
        'console_scripts': [
            'ios-bridge=ios_bridge_cli.cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires='>=3.8',
)