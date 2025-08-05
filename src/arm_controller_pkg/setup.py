from setuptools import find_packages, setup

package_name = 'arm_controller_pkg'

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
    maintainer='yasukawa_lab',
    maintainer_email='yasukawa_lab@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
    'console_scripts': [
        'arm_controller = arm_controller_pkg.arm_controller:main', 
        'arm_smooth_controller = arm_controller_pkg.arm_smooth_controller:main', 
        'arm_client_node = arm_controller_pkg.arm_client_node:main', 
        'arm_controller_server_d435 = arm_controller_pkg.arm_controller_server_d435:main', 
        'arm_client_node_d435 = arm_controller_pkg.arm_client_node_d435:main', 
        'arm_controller_teleop = arm_controller_pkg.arm_controller_teleop:main',
        'arm_controller_teleop_angle = arm_controller_pkg.arm_controller_teleop_angle:main',
        ],
    },
)
