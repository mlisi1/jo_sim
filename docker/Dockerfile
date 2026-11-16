FROM osrf/ros:jazzy-desktop-full

ENV GZ_VERSION=harmonic
ARG DISTRO=jazzy

# ── Pinned versions (override with --build-arg or in .env) ─────────────────
# Keep GLIM / CUDA in sync with jo-zotac.
ARG CUDA_VERSION=13-1
ARG CUDA_DIR=13.1
# koide3/glim; >= 1a197c9 needed by glim_ros2@dev (contains the a9be365 GTSAM 4.3 fix)
ARG GLIM_REF=1a197c999e4865f5cab7c9cd25474128413ebbca
# koide3/gtsam_points, built from source: GLIM master needs IndexedSlidingWindow::has_index,
# which is newer than the last release (1.2.2, the newest version in the koide3 PPA)
ARG GTSAM_POINTS_REF=8e94654558dfbe7ddb0341de300daaf17e25ee02
# CUDA architectures for gtsam_points ("native" cannot work: no GPU during docker build).
# all-major runs on any GPU; set e.g. 120 (RTX 50xx) in .env for a faster build.
ARG CUDA_ARCHS=all-major
# mlisi1/glim_ros2 branch / tag / commit
ARG GLIM_ROS_REF=dev
ARG RGL_REF=07b5f2ed244c9cfbd5ef12066d1c3e47f5eedbc6
ARG NAV2_CONFIG_REF=6525a324cec2bd5d308dc7ad931888d9b745545b
# RTAB-Map from source is slow and memory hungry
ARG BUILD_RTABMAP=false
ARG RTABMAP_REF=7d8b585217033e8d25d01b380a36744effe816df
ARG RTABMAP_ROS_REF=3e1cdcb072ad21fa2b129412332760bd3e456279
# DendROS release tag, or "latest"
ARG DENDROS_VERSION=latest
ARG BUILD_JOBS=8

RUN apt update -y \
    && apt install -y python3-pip \
    nano \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install --break-system-packages ruamel.yaml PyQt6

RUN apt update -y \
    && apt install -y ros-${DISTRO}-plotjuggler \
    ros-${DISTRO}-joint-state-publisher \
    ros-${DISTRO}-joint-state-publisher-gui \
    ros-${DISTRO}-gz-ros2-control \
    ros-${DISTRO}-teleop-twist-joy \
    ros-${DISTRO}-teleop-twist-keyboard \
    ros-${DISTRO}-joy \
    ros-${DISTRO}-ros2-control \
    ros-${DISTRO}-ros2-controllers \
    ros-${DISTRO}-xacro \
    ros-${DISTRO}-rosbag2-storage-mcap \
    ros-${DISTRO}-rmw-cyclonedds-cpp \
    ros-${DISTRO}-velodyne-laserscan \
    ros-${DISTRO}-realsense2-camera \
    ros-${DISTRO}-realsense2-description \
    ros-${DISTRO}-twist-mux \
    ros-${DISTRO}-nav2-common \
    ros-${DISTRO}-nav2-controller \
    ros-${DISTRO}-nav2-smoother \
    ros-${DISTRO}-nav2-planner \
    ros-${DISTRO}-nav2-behaviors \
    ros-${DISTRO}-nav2-bt-navigator \
    ros-${DISTRO}-nav2-waypoint-follower \
    ros-${DISTRO}-nav2-velocity-smoother \
    ros-${DISTRO}-nav2-lifecycle-manager \
    ros-${DISTRO}-nav2-dwb-controller \
    ros-${DISTRO}-nav2-navfn-planner \
    ros-${DISTRO}-nav2-rviz-plugins \
    ros-${DISTRO}-nav2-graceful-controller \
    ros-${DISTRO}-nav2-map-server \
    ros-${DISTRO}-robot-localization \
    ros-${DISTRO}-diagnostic-updater \
    ros-${DISTRO}-diagnostic-msgs \
    ros-${DISTRO}-std-srvs \
    python3-rosdep \
    python3-yaml \
    software-properties-common \
    ca-certificates \
    libmetis-dev \
    gnupg \
    wget \
    xterm \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt update -y \
    && apt install -y gz-harmonic \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# ── CUDA (Ubuntu 24.04) + GLIM dependencies ───────────────────────────────
RUN wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb \
 && dpkg -i cuda-keyring_1.1-1_all.deb && rm cuda-keyring_1.1-1_all.deb \
 && wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-ubuntu2404.pin \
 && mv cuda-ubuntu2404.pin /etc/apt/preferences.d/cuda-repository-pin-600

# GTSAM 4.3 and iridescence from the koide3 PPA; gtsam_points from source (see GTSAM_POINTS_REF)
RUN curl -s https://koide3.github.io/ppa/setup_ppa.sh | bash \
 && add-apt-repository -y ppa:koide3/iridescence \
 && apt update -y \
 && apt install -y libiridescence-dev \
    libgtsam-notbb-dev \
    cuda-cudart-dev-${CUDA_VERSION} \
    cuda-nvcc-${CUDA_VERSION} \
    cuda-cccl-${CUDA_VERSION} \
    cuda-driver-dev-${CUDA_VERSION} \
    libcurand-dev-${CUDA_VERSION} \
    libcusparse-dev-${CUDA_VERSION} \
    libcusolver-dev-${CUDA_VERSION} \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PATH=/usr/local/cuda-${CUDA_DIR}/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda-${CUDA_DIR}/lib64:${LD_LIBRARY_PATH}
ENV CUDAToolkit_ROOT=/usr/local/cuda-${CUDA_DIR}

RUN mkdir -p /tmp/gtsam_points && cd /tmp/gtsam_points && git init -q \
 && git remote add origin https://github.com/koide3/gtsam_points.git \
 && git fetch -q --depth 1 origin ${GTSAM_POINTS_REF} && git checkout -q FETCH_HEAD \
 && cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_WITH_CUDA=ON \
      -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHS}" \
 && cmake --build build -j${BUILD_JOBS} && cmake --install build \
 && ldconfig && rm -rf /tmp/gtsam_points


# ── Non-root user ──────────────────────────────────────────────────────────
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
RUN if id -u ${USER_UID} ; then userdel `id -un ${USER_UID}` ; fi
RUN groupadd --gid ${USER_GID} ${USERNAME}
RUN useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && apt update \
    && apt install -y sudo \
    && echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && usermod -aG dialout ${USERNAME} \
    && rm -rf /var/lib/apt/lists/*

USER ros
WORKDIR /home/${USERNAME}/
SHELL ["/bin/bash", "-c"]

# Clone a repo at a branch, tag or commit: clone_at <url> <ref> <dir>
RUN printf '%s\n' '#!/usr/bin/env bash' 'set -e' \
      'mkdir -p "$3" && cd "$3" && git init -q && git remote add origin "$1"' \
      'git fetch -q --depth 1 origin "$2" && git checkout -q FETCH_HEAD' \
      | sudo tee /usr/local/bin/clone_at > /dev/null \
 && sudo chmod +x /usr/local/bin/clone_at


# ── RGL GPU lidar plugin ───────────────────────────────────────────────────
RUN clone_at https://github.com/RobotecAI/RGLGazeboPlugin.git ${RGL_REF} RGLGazeboPlugin \
 && cd RGLGazeboPlugin && mkdir build && cd build \
 && cmake .. && make -j${BUILD_JOBS} && make install \
 && touch /home/ros/RGLGazeboPlugin/COLCON_IGNORE

# Set with ENV (not echo >> .bashrc) so they are available to every process and are
# appended to, not clobbered. The world/model resource paths are set by the launch files.
ENV RGL_PATTERNS_DIR=/home/ros/RGLGazeboPlugin/lidar_patterns
ENV GZ_SIM_SYSTEM_PLUGIN_PATH=/home/ros/RGLGazeboPlugin/install/RGLServerPlugin
ENV GZ_GUI_PLUGIN_PATH=/home/ros/RGLGazeboPlugin/install/RGLVisualize


# ── Workspace: GLIM, glim_ros2, tools ──────────────────────────────────────
RUN mkdir src \
 && clone_at https://github.com/koide3/glim.git ${GLIM_REF} src/glim \
 && clone_at https://github.com/mlisi1/glim_ros2.git ${GLIM_ROS_REF} src/glim_ros2 \
 && clone_at https://github.com/sutharsan-311/nav2_config.git ${NAV2_CONFIG_REF} src/nav2_config

RUN source /opt/ros/${DISTRO}/setup.bash \
 && MAKEFLAGS="-j${BUILD_JOBS}" colcon build --parallel-workers 2 --cmake-args -DCMAKE_BUILD_TYPE=Release


# ── RTAB-Map (optional) ────────────────────────────────────────────────────
# Same approach as jo-zotac: built one package at a time, because building the
# ~14 rtabmap* packages in parallel runs out of memory.
RUN if [ "${BUILD_RTABMAP}" = "true" ]; then \
      clone_at https://github.com/introlab/rtabmap.git ${RTABMAP_REF} src/rtabmap \
   && clone_at https://github.com/introlab/rtabmap_ros.git ${RTABMAP_ROS_REF} src/rtabmap_ros \
   && source /opt/ros/${DISTRO}/setup.bash \
   && MAKEFLAGS="-j6" colcon build --packages-select-regex '^rtabmap.*' --executor sequential \
        --cmake-args -DRTABMAP_SYNC_MULTI_RGBD=ON -DRTABMAP_SYNC_USER_DATA=ON -DCMAKE_BUILD_TYPE=Release ; \
    else echo "Skipping RTAB-Map (BUILD_RTABMAP=${BUILD_RTABMAP})" ; fi


# ── DendROS (latest release unless pinned) ─────────────────────────────────
RUN TAG="${DENDROS_VERSION}" \
 && if [ "$TAG" = "latest" ]; then \
      TAG=$(git ls-remote --tags --refs --sort=-v:refname https://github.com/mlisi1/DendROS.git | head -1 | sed 's|.*/||'); fi \
 && echo "Installing DendROS ${TAG}" \
 && git clone -q --depth 1 --branch "${TAG}" https://github.com/mlisi1/DendROS.git /tmp/DendROS \
 && bash /tmp/DendROS/install.sh -y \
 && sudo rm -rf /tmp/DendROS


COPY docker/entrypoint.sh /entrypoint.sh
RUN sudo chmod +x /entrypoint.sh

# utilities.sh is mounted at runtime (./docker/utils), so it can change without a rebuild
RUN echo '[ -f /home/ros/utils/utilities.sh ] && source /home/ros/utils/utilities.sh' >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
