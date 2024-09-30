from pathlib import Path
from setuptools import find_namespace_packages, setup

with open("requirements.in") as f:
    REQUIREMENTS = [line for line in f if line and line[0] not in "#-"]

with open("test-requirements.in") as f:
    TEST_REQUIREMENTS = [line for line in f if line and line[0] not in "#-"]

version = Path("VERSION").read_text(encoding="utf-8").strip()

setup(
    name="kiwi-structlog-config",
    version=version,
    url="https://github.com/kiwicom/kiwi-structlog-config",
    author="Booking Backend team",
    author_email="bookingbe@kiwi.com",
    packages=find_namespace_packages(),
    install_requires=REQUIREMENTS,
    tests_require=TEST_REQUIREMENTS,
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
)
