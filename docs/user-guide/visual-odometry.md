# Visual odometry (RTAB-Map)

The robot's stack can run RTAB-Map on the front camera: visual odometry and, on request, visual
SLAM. RTAB-Map is **optional** and isn't in the default image, because it takes a long time and a
lot of memory to build.

<figure class="jo-media">
<video src="../../assets/videos/rtabmap.mp4" poster="../../assets/videos/rtabmap.jpg" autoplay muted loop playsinline></video>
<figcaption>RTAB-Map in office_cpr (2× speed), as Nav2 drives Jo along the corridor and back. RViz
shows the occupancy grid (<code>/visodom/map</code>) and the graph (<code>/visodom/mapPath</code>,
amber). On the right, from the top: Gazebo, RTAB-Map's own visualizer and the front camera.</figcaption>
</figure>

## Build the image with RTAB-Map

Set `BUILD_RTABMAP=true` in `.env`, then rebuild and recreate the container:

```bash
./jo down
docker compose build
./jo up
```

With a warm cache this takes about 20 minutes on 8 jobs. To keep your current image next to it, see
[Docker image](../developer/docker.md#building).

## Run it

| Command | What runs |
|---|---|
| `./jo sim -n local` | Visual odometry starts by itself when RTAB-Map is installed |
| `./jo sim -n local vslam:=true` | Visual odometry and RTAB-Map SLAM (mapping mode) |
| `./jo sim -n local visodom:=false` | Neither |

Without RTAB-Map in the image, the stack skips these nodes and runs normally.

## Topics and files

| Output | Type | Notes |
|---|---|---|
| `/visodom/odom` | `nav_msgs/Odometry` | Visual odometry of `base_link`, from the front camera |
| `/visodom/map` | `nav_msgs/OccupancyGrid` | 2D grid from the lidar, 5 cm cells, frame `vslam_map` (`vslam:=true`) |
| `/visodom/mapPath` | `nav_msgs/Path` | The graph's poses, frame `vslam_map` (`vslam:=true`) |
| `/visodom/info` | `rtabmap_msgs/Info` | Status of each update, including loop closures (`vslam:=true`) |
| `saved_maps/<date>_<time>_rtabmap/rtabmap.db` | RTAB-Map database | A new one for every `vslam:=true` run |

!!! note "`vslam_map` isn't in the TF tree"
    RTAB-Map publishes no TF here, so it can't conflict with the frames GLIM and the EKF own. To
    see its output in RViz, set **Fixed Frame** to `vslam_map`. The robot model can't be shown in
    that frame.

The EKF configuration lists `/visodom/odom` as a second odometry source (`odom1` in
`localization.yaml`), so with RTAB-Map installed the EKF also fuses it.

## RTAB-Map's visualizer

`rtabmap_viz` shows what RTAB-Map is doing: the features tracked in each image, the loop closure
candidates and the 3D map. The stack doesn't start it, so open it yourself in a second shell
(`./jo shell`) while the simulation runs with `vslam:=true`:

```bash
ros2 run rtabmap_viz rtabmap_viz --ros-args -r __ns:=/visodom \
  -p use_sim_time:=true -p frame_id:=base_link -p subscribe_depth:=true -p subscribe_rgb:=false \
  -p subscribe_odom_info:=true -p subscribe_scan_cloud:=false \
  -p approx_sync:=true -p approx_sync_max_interval:=0.05 -p topic_queue_size:=30 -p sync_queue_size:=30 \
  -p image_transport:=compressed -p depth_transport:=compressedDepth \
  -r rgb/image:=/front_camera/camera/color/image_raw \
  -r rgb/camera_info:=/front_camera/camera/color/camera_info \
  -r depth/image:=/front_camera/camera/aligned_depth_to_color/image_raw \
  -r odom:=/visodom/odom -r odom_info:=/visodom/odom_info
```

| Panel | Shows |
|---|---|
| **Loop closure detection** | The current image, and the earlier image it is matched against |
| **Odometry** | The features visual odometry is tracking in the current image |
| **3D Map** | The point cloud, the trajectory and the graph |

## What to expect

One `vslam:=true` run in office_cpr, the one in the video, compared with the
[ground truth](ground-truth.md):

| Measure | Result |
|---|---|
| Distance driven | 7.3 m, out and back |
| Visual odometry error | 11 cm at the end, 12.5 cm at most |
| Tracking | Never lost |
| Graph | 17 poses |
| Mapped area | 210 m² |
| Database | 33 MB |

RTAB-Map found 4 proximity links between nearby poses and accepted no global loop closure. Near
plain walls, `rgbd_odometry` can warn `Not enough points with valid depth`. It kept tracking through
these warnings in this run.
