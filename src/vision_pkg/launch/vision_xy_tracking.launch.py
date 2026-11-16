"""Real D405 or synthetic fixed-target camera with the separate XY tracker."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path
import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject accidental replacement of a whole settings block before startup."""
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = {}
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    f'first definition of {key!r}', seen[key],
                    f'duplicate YAML key {key!r}; combine these settings in one block',
                    key_node.start_mark)
            seen[key] = key_node.start_mark
        return super().construct_mapping(node, deep=deep)


def nodes(context):
    config_path = Path(LaunchConfiguration('config_file').perform(context)).expanduser().resolve()
    with config_path.open(encoding='utf-8') as stream:
        config = yaml.load(stream, Loader=UniqueKeyLoader)
    if not isinstance(config, dict) or config.get('config_schema') != 'vision_xy_tracking/v1':
        raise RuntimeError('config_file must be a unified vision_xy_tracking/v1 YAML')
    for name in ('launch', 'tracking', 'startup', 'z_tracking', 'ik_solver_params',
                 'dxl_params', 'camera', 'detector', 'target'):
        if not isinstance(config.get(name), dict):
            raise RuntimeError(f'{config_path}: {name} must be a mapping')

    defaults = dict(backend='sim', startup_mode='configured', synthetic_camera=False,
                    show_window=True, z_tracking_enabled=False, harvest_cycle_enabled=True,
                    require_ee_ready=False)
    unknown = set(config['launch'])-set(defaults)
    if unknown:
        raise RuntimeError(f'Unknown launch settings: {sorted(unknown)}')
    options = dict(defaults, **config['launch'])
    for name, default in defaults.items():
        override = LaunchConfiguration(name).perform(context).strip()
        if override:
            if isinstance(default, bool):
                if override.lower() not in ('true', 'false'):
                    raise RuntimeError(f'{name} must be true or false')
                options[name] = override.lower() == 'true'
            else:
                options[name] = override
        if isinstance(default, bool) and not isinstance(options[name], bool):
            raise RuntimeError(f'launch.{name} must be a YAML boolean')
    backend = options['backend']
    if backend not in ('sim', 'dynamixel', 'can_mixed'):
        raise RuntimeError('backend must be sim, dynamixel, or can_mixed')
    if options['startup_mode'] not in ('configured', 'current'):
        raise RuntimeError('startup_mode must be configured or current')
    synthetic = options['synthetic_camera']
    if synthetic and backend != 'sim':
        raise RuntimeError('synthetic_camera is allowed only with backend:=sim')
    vision_override = LaunchConfiguration('vision_config').perform(context).strip()
    vision_path = Path(vision_override).expanduser().resolve() if vision_override else config_path
    if not vision_path.is_file():
        raise RuntimeError(f'Vision config not found: {vision_path}')
    tracking = dict(config['tracking'])
    reserved = set(tracking) & (set(defaults) | {'config_file'})
    if reserved:
        raise RuntimeError(f'Put {sorted(reserved)} in launch:, not tracking:')
    tracking.update(config_file=str(config_path), backend=backend,
                    harvest_cycle_enabled=options['harvest_cycle_enabled'],
                    require_ee_ready=options['require_ee_ready'],
                    z_tracking_enabled=options['z_tracking_enabled'],
                    startup_mode=options['startup_mode'])
    message = f'Unified tracking config: {config_path}'
    if vision_override:
        message += f'; legacy vision_config override: {vision_path}'
    return [LogInfo(msg=message),
            Node(package='arm_controller_pkg', executable='arm_xy_tracker', output='screen',
                 parameters=[tracking]),
            Node(package='vision_pkg', executable='vision_service_realtime', output='screen',
                 parameters=[{'config_file': str(vision_path),
                              'z_tracking_enabled': options['z_tracking_enabled'],
                              'synthetic_camera': synthetic,
                              'harvest_cycle_enabled': options['harvest_cycle_enabled'],
                              'show_window': options['show_window']}])]


def generate_launch_description():
    config = str(Path(get_package_share_directory('vision_pkg'))/'config/vision_xy_tracking.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('config_file', default_value=config,
            description='Single YAML for launch options, tracker, robot, and vision settings'),
        DeclareLaunchArgument('backend', default_value='', description='Override launch.backend in YAML'),
        DeclareLaunchArgument('startup_mode', default_value=''),
        DeclareLaunchArgument('harvest_cycle_enabled', default_value=''),
        DeclareLaunchArgument('require_ee_ready', default_value=''),
        DeclareLaunchArgument('synthetic_camera', default_value=''),
        DeclareLaunchArgument('show_window', default_value=''),
        DeclareLaunchArgument('z_tracking_enabled', default_value='',
            description='Enable depth-free pixel-band Z correction; requires Z_TRACKING_V1 firmware on hardware'),
        DeclareLaunchArgument('vision_config', default_value='',
            description='Optional legacy vision-only override; normally leave empty'),
        OpaqueFunction(function=nodes),
    ])
