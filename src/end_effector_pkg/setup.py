from setuptools import find_packages, setup

package_name = 'end_effector_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README_auto_harvest_ja.md']),
        ('share/' + package_name + '/config', ['config/auto_harvest.yaml']),
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
            'suction_module_node = end_effector_pkg.suction_module_node:main',
            'suction_module_service_node = end_effector_pkg.suction_module_service_node:main',
            'suction_module_client_node = end_effector_pkg.suction_module_client_node:main',
            'suction_module_teleop = end_effector_pkg.suction_module_teleop:main',
            'end_effector_teleop = end_effector_pkg.end_effector_teleop:main',
            'pull_module_teleop = end_effector_pkg.pull_module_teleop:main',
            'auto_harvest = end_effector_pkg.auto_harvest_node:main',
        ],
    },
)
