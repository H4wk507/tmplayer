#!/usr/bin/env python3

import os
from typing import Any

from setuptools import find_packages, setup


def read_file(fname: str) -> str:
    with open(fname, encoding="utf-8") as f:
        return f.read()


def read_version(fname: str) -> Any:
    exec(compile(read_file(fname), fname, "exec"))
    return locals()["__version__"]


directory = os.path.abspath(os.path.dirname(__file__))

VERSION = read_version(os.path.join(directory, "tmpl", "version.py"))

DESCRIPTION = "Minimalist music player for audio files with a pleasant UI."

LONG_DESCRIPTION = read_file(os.path.join(directory, "README.md"))

REQUIREMENTS = read_file(
    os.path.join(directory, "requirements.txt")
).splitlines()

setup(
    name="tmpl2",
    version=VERSION,
    description=DESCRIPTION,
    author="Piotr Skowroński",
    license="MIT",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Topic :: Multimedia :: Sound/Audio",
        "Environment :: Console",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "console_scripts": [
            "tmpl2=tmpl.main:main",
        ],
    },
    install_requires=REQUIREMENTS,
    python_requires=">=3.10",
    extras_require={
        "formatting": [
            "black",
        ],
        "linting": [
            "flake8",
            "mypy",
        ],
    },
)
