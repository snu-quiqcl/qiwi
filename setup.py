"""
Set-up file for releasing this package.
"""

from setuptools import setup

with open("requirements.txt") as f:
    required = f.read().splitlines()


setup(
    name="qiwis",
    version="3.0.1",
    author="QuIQCL",
    author_email="kangz12345@snu.ac.kr",
    url="https://github.com/snu-quiqcl/qiwis",
    description="QuIqcl Widget Integration Software",
    long_description=
        "A framework for integration of PyQt widgets where they can communicate with each other. "
        "This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.",
    download_url="https://github.com/snu-quiqcl/qiwis/releases/tag/v3.0.1",
    license="MIT license",
    python_requires=">=3.8",
    install_requires=required,
    py_modules=["qiwis"],
    entry_points={
        "console_scripts": ["qiwis = qiwis:main"]
    }
)
