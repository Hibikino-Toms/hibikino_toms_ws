from setuptools import find_packages, setup

package_name = 'vision_pkg'

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
    maintainer_email='ylab@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vision_service = vision_pkg.vision_service:main',
            'vision_service_d435 = vision_pkg.vision_service_d435:main',
            'vision_client_node = vision_pkg.vision_client_node:main',
            'vision_client_d435_node = vision_pkg.vision_client_d435_node:main',
        ],
    },
)
