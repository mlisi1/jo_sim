cmake_minimum_required(VERSION 3.8)
project(jo_sim)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(frame_restamp src/frame_restamp.cpp)
target_compile_features(frame_restamp PUBLIC cxx_std_17)
target_link_libraries(frame_restamp PUBLIC rclcpp::rclcpp ${sensor_msgs_TARGETS})

add_executable(velodyne_emulation src/velodyne_emulation.cpp)
target_compile_features(velodyne_emulation PUBLIC cxx_std_17)
target_link_libraries(velodyne_emulation PUBLIC rclcpp::rclcpp ${sensor_msgs_TARGETS})

install(TARGETS frame_restamp velodyne_emulation DESTINATION lib/${PROJECT_NAME})

# jo_sim.world_tools (used by the launch files and list_worlds)
ament_python_install_package(${PROJECT_NAME})

install(
  PROGRAMS scripts/list_worlds scripts/check_worlds scripts/realsense_tf scripts/gui_follow scripts/sim_control
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

# Built-in worlds; the external collection (thousands of files) is installed as one symlink
# (an install(DIRECTORY ... EXCLUDE) is not honoured by --symlink-install)
file(GLOB WORLD_FILES LIST_DIRECTORIES false worlds/*)
install(FILES ${WORLD_FILES} DESTINATION share/${PROJECT_NAME}/worlds)
install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E rm -rf
  \$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME}/worlds/external)")
install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink
  ${CMAKE_CURRENT_SOURCE_DIR}/worlds/external
  \$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME}/worlds/external)")

ament_package()
