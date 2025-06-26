from setuptools import find_packages, setup

package_name = 'harvest_task_pkg'

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
            'harvest_state_machine = harvest_task_pkg.harvest_state_machine:main',
            'harvest_state_machine_test = harvest_task_pkg.harvest_state_machine_test:main',
            'harvest_task_cart_state = harvest_task_pkg.harvest_task_cart_state:main',
            'analyze_to_harvest_client = harvest_task_pkg.analyze_to_harvest_client:main',
            'demo = harvest_task_pkg.demo:main',
        ],
    },
)
