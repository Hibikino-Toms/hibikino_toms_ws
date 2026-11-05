from setuptools import find_packages, setup

package_name = 'vision_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README_realtime_ja.md']),
        ('share/' + package_name + '/config', ['config/realtime_detector.yaml']),
        ('share/' + package_name + '/launch', ['launch/vision_service_realtime.launch.py']),
        ('share/' + package_name + '/launch', ['launch/vision_xy_tracking.launch.py']),
        ('share/' + package_name + '/launch', ['launch/vision_auto_harvest.launch.py']),
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
            # 追加2025/11/03,  vision_serviceをipad操作用に改良したもの
            'vision_service_ipad = vision_pkg.vision_service_ipad:main',
            # 追加2026/05/12, 短縮のためにカメラの取り合いを解消 
            'vision_service_ipad_rev2 = vision_pkg.vision_service_ipad_rev2:main',
            # 追加2025/11/07, realsenseのフレームをパプリッシュするノード
            'cam_pub_service = vision_pkg.cam_pub_service:main',
            # 追加2026/03/04, カメラ視点の切り替え追加
            'cam_pub_service_rev2 = vision_pkg.cam_pub_service_rev2:main',
            'vision_service_ipad_dual_topic = vision_pkg.vision_service_ipad_dual_topic:main',
            'vision_service_bench = vision_pkg.vision_service_bench:main',
            'vision_service_realtime = vision_pkg.vison_sevice_realtime:main',
        ],
    },
)
