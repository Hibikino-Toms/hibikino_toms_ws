from setuptools import find_packages
from setuptools import setup

setup(
    name='toms_msg',
    version='0.0.0',
    packages=find_packages(
        include=('toms_msg', 'toms_msg.*')),
)
