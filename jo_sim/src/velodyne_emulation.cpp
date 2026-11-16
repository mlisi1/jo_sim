// Turns the RGL lidar cloud (x, y, z, intensity) into what the Velodyne VLP-16 driver publishes
// (velodyne_pointcloud transform node): fields x, y, z, intensity (FLOAT32), ring (UINT16),
// time (FLOAT32), with the driver's range limits.
//
// * ring: laser index from the elevation angle (VLP-16: -15 deg .. +15 deg every 2 deg, ring 0 at
//   the bottom), needed by velodyne_laserscan (/scan) and used by GLIM (ring_field).
// * time: 0 for every point. The simulated sweep is captured at one instant, so there is no motion
//   distortion to correct; real per-point times would make GLIM "deskew" an undistorted cloud.
// * optional Gaussian range noise along each ray (the RGL plugin has no noise model):
//   p' = p * (r + n) / r, n ~ N(0, range_stddev); 0 disables it.
// * points outside [min_range, max_range] are dropped. The cloud is unorganized (height 1), the
//   real driver organizes it by ring (organize_cloud: true): consumers in our stack do not care.
//
// Topics: input -> output (remap them). Parameters: range_stddev [m], min_range, max_range,
// vertical_fov_min_deg, vertical_step_deg, rings, seed.
#include <algorithm>
#include <cmath>
#include <cstring>
#include <memory>
#include <random>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/msg/point_field.hpp"

using sensor_msgs::msg::PointCloud2;
using sensor_msgs::msg::PointField;

class VelodyneEmulation : public rclcpp::Node
{
public:
  explicit VelodyneEmulation(const rclcpp::NodeOptions & options)
  : Node("velodyne_emulation", options),
    stddev_(declare_parameter<double>("range_stddev", 0.0)),
    min_range_(declare_parameter<double>("min_range", 0.9)),
    max_range_(declare_parameter<double>("max_range", 130.0)),
    fov_min_(declare_parameter<double>("vertical_fov_min_deg", -15.0)),
    step_(declare_parameter<double>("vertical_step_deg", 2.0)),
    rings_(declare_parameter<int>("rings", 16)),
    rng_(static_cast<std::mt19937::result_type>(declare_parameter<int>("seed", 0))),
    dist_(0.0, stddev_ > 0.0 ? stddev_ : 1.0)
  {
    // ~10 MB-class clouds: reliable, best effort loses fragments
    pub_ = create_publisher<PointCloud2>("output", rclcpp::QoS(10));
    sub_ = create_subscription<PointCloud2>(
      "input", rclcpp::QoS(10),
      [this](PointCloud2::ConstSharedPtr msg) {convert(*msg);});
  }

private:
  static int offset(const PointCloud2 & msg, const std::string & name)
  {
    for (const auto & f : msg.fields) {
      if (f.name == name && f.datatype == PointField::FLOAT32) {
        return static_cast<int>(f.offset);
      }
    }
    return -1;
  }

  static PointField field(const std::string & name, uint32_t off, uint8_t type)
  {
    PointField f;
    f.name = name;
    f.offset = off;
    f.datatype = type;
    f.count = 1;
    return f;
  }

  void convert(const PointCloud2 & in)
  {
    const int ox = offset(in, "x"), oy = offset(in, "y"), oz = offset(in, "z");
    const int oi = offset(in, "intensity");
    if (ox < 0 || oy < 0 || oz < 0) {
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 5000, "input cloud has no FLOAT32 x/y/z");
      return;
    }

    auto out = std::make_unique<PointCloud2>();
    out->header = in.header;
    out->height = 1;
    out->is_bigendian = false;
    out->is_dense = true;
    // Same layout as velodyne_pointcloud's PointXYZIRT
    out->fields = {
      field("x", 0, PointField::FLOAT32), field("y", 4, PointField::FLOAT32),
      field("z", 8, PointField::FLOAT32), field("intensity", 12, PointField::FLOAT32),
      field("ring", 16, PointField::UINT16), field("time", 18, PointField::FLOAT32)};
    out->point_step = 22;
    const size_t n = static_cast<size_t>(in.width) * in.height;
    out->data.resize(n * out->point_step);

    size_t kept = 0;
    for (size_t i = 0; i < n; ++i) {
      const uint8_t * src = in.data.data() + i * in.point_step;
      float p[3], intensity = 0.0f;
      std::memcpy(&p[0], src + ox, 4);
      std::memcpy(&p[1], src + oy, 4);
      std::memcpy(&p[2], src + oz, 4);
      if (oi >= 0) {
        std::memcpy(&intensity, src + oi, 4);
      }
      const double h = std::hypot(p[0], p[1]);
      const double r = std::hypot(h, p[2]);
      if (!std::isfinite(r) || r < min_range_ || r > max_range_) {
        continue;
      }
      if (stddev_ > 0.0) {
        const double s = (r + dist_(rng_)) / r;
        for (float & v : p) {
          v = static_cast<float>(v * s);
        }
      }
      const double elev = std::atan2(p[2], h) * 180.0 / M_PI;
      const auto ring = static_cast<uint16_t>(
        std::clamp(static_cast<int>(std::lround((elev - fov_min_) / step_)), 0, rings_ - 1));
      const float t = 0.0f;

      uint8_t * dst = out->data.data() + kept * out->point_step;
      std::memcpy(dst + 0, &p[0], 4);
      std::memcpy(dst + 4, &p[1], 4);
      std::memcpy(dst + 8, &p[2], 4);
      std::memcpy(dst + 12, &intensity, 4);
      std::memcpy(dst + 16, &ring, 2);
      std::memcpy(dst + 18, &t, 4);
      ++kept;
    }
    out->width = static_cast<uint32_t>(kept);
    out->row_step = out->width * out->point_step;
    out->data.resize(kept * out->point_step);
    pub_->publish(std::move(out));
  }

  double stddev_, min_range_, max_range_, fov_min_, step_;
  int rings_;
  std::mt19937 rng_;
  std::normal_distribution<double> dist_;
  rclcpp::Publisher<PointCloud2>::SharedPtr pub_;
  rclcpp::Subscription<PointCloud2>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<VelodyneEmulation>(rclcpp::NodeOptions()));
  rclcpp::shutdown();
  return 0;
}
