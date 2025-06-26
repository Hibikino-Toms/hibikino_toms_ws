from setuptools import find_packages, setup

package_name = 'cart_controller_pkg'

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
        'rail_service_node = cart_controller_pkg.rail_service_node:main',
        'rail_client_node = cart_controller_pkg.rail_client_node:main',
        'crawler_service_node = cart_controller_pkg.crawler_service_node:main',
        'crawler_client_node = cart_controller_pkg.crawler_client_node:main',
        ],
    },
)
