from setuptools import find_packages, setup

setup(
    name="israel_bus_locator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    author="Jon Zarecki",
    description="Python package for exploring Israel bus location data",
    python_requires=">=3.8",
)
