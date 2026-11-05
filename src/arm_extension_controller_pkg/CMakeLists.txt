cmake_minimum_required(VERSION 3.8)
project(arm_extension_controller_pkg)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "srv/MoveArm.srv")
ament_export_dependencies(rosidl_default_runtime)
# Python nodes + generated service stay in this one package.
install(PROGRAMS scripts/arm_service_node.py
  DESTINATION lib/${PROJECT_NAME} RENAME arm_service_node)
install(PROGRAMS scripts/arm_client_node.py
  DESTINATION lib/${PROJECT_NAME} RENAME arm_client_node)
install(FILES scripts/arm_driver.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY firmware DESTINATION share/${PROJECT_NAME})
install(FILES README.md DESTINATION share/${PROJECT_NAME})
ament_package()
