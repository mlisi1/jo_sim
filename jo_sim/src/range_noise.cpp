// Adds Gaussian range noise to a PointCloud2 (the RGL lidar plugin has no noise model).
// Every point is moved along its ray: p' = p * (r + n) / r, n ~ N(0, range_stddev).
// Needs FLOAT32 x, y, z fields; everything else (intensity, ring, time, ...) is kept.
//
// Topics: ~/input -> ~/output (remap them). Parameters: range_stddev [m], seed.
#include <cmath>
#include <cstring>
#include <memory>
#include <random>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"

class RangeNoise : public rclcpp::Node
{
public:
  explicit RangeNoise(const rclcpp::NodeOptions & options)
  : Node("range_noise", options),
    stddev_(declare_parameter<double>("range_stddev", 0.015)),
    rng_(static_cast<std::mt19937::result_type>(declare_parameter<int>("seed", 0))),
    dist_(0.0, stddev_)
  {
    pub_ = create_publisher<sensor_msgs::msg::PointCloud2>("output", rclcpp::QoS(10));
    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      "input", rclcpp::QoS(10),
      [this](sensor_msgs::msg::PointCloud2::UniquePtr msg) {
        add_noise(*msg);
        pub_->publish(std::move(msg));
      });
  }

private:
  void add_noise(sensor_msgs::msg::PointCloud2 & msg)
  {
    int off[3] = {-1, -1, -1};
    const char * names[3] = {"x", "y", "z"};
    for (const auto & f : msg.fields) {
      for (int i = 0; i < 3; ++i) {
        if (f.name == names[i] && f.datatype == sensor_msgs::msg::PointField::FLOAT32) {
          off[i] = static_cast<int>(f.offset);
        }
      }
    }
    if (off[0] < 0 || off[1] < 0 || off[2] < 0 || stddev_ <= 0.0) {
      return;
    }
    const size_t n = static_cast<size_t>(msg.width) * msg.height;
    for (size_t i = 0; i < n; ++i) {
      uint8_t * pt = msg.data.data() + i * msg.point_step;
      float p[3];
      for (int k = 0; k < 3; ++k) {
        std::memcpy(&p[k], pt + off[k], sizeof(float));
      }
      const double r = std::sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]);
      if (!std::isfinite(r) || r < 1e-6) {
        continue;
      }
      const double s = (r + dist_(rng_)) / r;
      for (int k = 0; k < 3; ++k) {
        const float v = static_cast<float>(p[k] * s);
        std::memcpy(pt + off[k], &v, sizeof(float));
      }
    }
  }

  double stddev_;
  std::mt19937 rng_;
  std::normal_distribution<double> dist_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<RangeNoise>(rclcpp::NodeOptions()));
  rclcpp::shutdown();
  return 0;
}
