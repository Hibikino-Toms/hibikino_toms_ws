from setuptools import setup

package_name = 'cart_module_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ilab',
    maintainer_email='ilab@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'move_cart_client = cart_module_ros2.move_cart_client:main',
            'move_cart_server = cart_module_ros2.move_cart_server:main',
        ],
    },
)
