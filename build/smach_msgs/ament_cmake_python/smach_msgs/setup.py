from setuptools import find_packages
from setuptools import setup

setup(
    name='smach_msgs',
    version='2.0.1',
    packages=find_packages(
        include=('smach_msgs', 'smach_msgs.*')),
)
