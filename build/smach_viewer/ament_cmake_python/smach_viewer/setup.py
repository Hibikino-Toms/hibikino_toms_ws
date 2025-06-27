from setuptools import find_packages
from setuptools import setup

setup(
    name='smach_viewer',
    version='3.0.1',
    packages=find_packages(
        include=('smach_viewer', 'smach_viewer.*')),
)
