cmake_minimum_required(VERSION 3.8)
project(toms_msg)

set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

set(msg_files
"msg/TomatoPos.msg"
"msg/TomatoData.msg"
)

set(srv_files
"srv/VisionService.srv"
"srv/CrawlerService.srv"
"srv/RailService.srv"
"srv/ArmService.srv"
"srv/EndEffectorService.srv"
"srv/SuctionCommand.srv"
"srv/CartService.srv"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${srv_files}
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
