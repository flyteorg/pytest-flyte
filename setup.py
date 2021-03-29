#!/usr/bin/env python3

from setuptools import find_packages, setup


setup(
    name="pytest-flyte",
    version="0.0.0+dev0",
    packages=find_packages("src"),
    entry_points={"pytest11": ["flyte = pytest_flyte"]},
    package_dir={"": "src"},
    description="Pytest fixtures for simplifying Flyte integration testing",
    include_package_data=True,
    install_requires=[
        "docker-compose",
        "flytekit",
        "jinja2",
        "pytest",
        "pytest-docker",
    ],
)
