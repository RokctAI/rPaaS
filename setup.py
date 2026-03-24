from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __init__.py
from paas import __version__ as version

setup(
    name="paas",
    version=version,
    description="PaaS App for Rokct",
    author="ROKCT.ai",
    author_email="admin@rokct.ai",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
