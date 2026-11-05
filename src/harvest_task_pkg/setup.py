import os # ★ インポート追加
from glob import glob # ★ インポート追加
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
        
        # ★ 以下を追記 (launchディレクトリ内の .launch.py ファイルを登録)
        (os.path.join('share', package_name, 'launch'), 
            glob(os.path.join('launch', '*.launch.py'))),
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
            
            # ★ 以下を追記 (新しい自動収穫ノードの登録)
            'auto_harvest = teleop_demo_pkg.teleop_automation:main',
            # ★ 2025/11/1に以下を追記(demo.pyを中継ノードとしたサービス通信のサーバー)
            'ipad_demo_relay = harvest_task_pkg.ipad_demo_relay:main',
            'ipad_demo_sync_relay = harvest_task_pkg.ipad_demo_sync_relay:main',
            # ★ 2026/5/12に追加　高速化のため手先アーム移動中にカメラ切り替えを呼び出し
            'ipad_demo_sync_relay_rev2 = harvest_task_pkg.ipad_demo_sync_relay_rev2:main',
        ],
    },
)