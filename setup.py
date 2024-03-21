#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

setup(
    author="Simon Raper",
    author_email="simon@coppelia.io",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Python Boilerplate contains all the boilerplate you need to create a Python package.",
    install_requires=["pandas", "langchain", "langchain_openai", "pypdf"],
    include_package_data=True,
    keywords="timeline_ai",
    name="timeline_ai",
    packages=find_packages(include=["timeline_ai", "timeline_ai.*"]),
    test_suite="tests",
    url="https://github.com/coppeliamla/timeline_ai",
    version="0.1.0",
    zip_safe=False,
)
