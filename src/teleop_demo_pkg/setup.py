from setuptools import find_packages, setup

package_name = 'teleop_demo_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ylab',
    maintainer_email='hibikinotoms2022@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_demo = teleop_demo_pkg.teleop_demo:main',
            'teleop_demo_angle = teleop_demo_pkg.teleop_demo_angle:main',
        ],
    },
)
