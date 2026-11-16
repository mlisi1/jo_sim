cmake_minimum_required(VERSION 3.8)
project(jo_sim)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(frame_restamp src/frame_restamp.cpp)
target_compile_features(frame_restamp PUBLIC cxx_std_17)
target_link_libraries(frame_restamp PUBLIC rclcpp::rclcpp ${sensor_msgs_TARGETS})

add_executable(range_noise src/range_noise.cpp)
target_compile_features(range_noise PUBLIC cxx_std_17)
target_link_libraries(range_noise PUBLIC rclcpp::rclcpp ${sensor_msgs_TARGETS})

install(TARGETS frame_restamp range_noise DESTINATION lib/${PROJECT_NAME})

# jo_sim.world_tools (used by the launch files and list_worlds)
ament_python_install_package(${PROJECT_NAME})

install(
  PROGRAMS scripts/list_worlds scripts/realsense_tf
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch worlds rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
