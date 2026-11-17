// Gazebo depth image (32FC1, metres) -> what the RealSense driver publishes for
// aligned_depth_to_color/image_raw (depth_format Z16): 16UC1, millimetres, 0 = no data.
//
// * NaN, +-inf, values <= 0 and values that do not fit in 16 bits (> 65.535 m) become 0, as the
//   RealSense reports missing depth.
// * Published through image_transport, so the plugin topics (compressedDepth, ...) exist as on the
//   robot. image_transport does not apply a remap of the base topic to its plugin topics, so the
//   output topic is a parameter (output_topic), not a remap.
//
// Topics: ~/input (remap it) -> output_topic.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <memory>
#include <string>

#include "image_transport/image_transport.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/image_encodings.hpp"
#include "sensor_msgs/msg/image.hpp"

class DepthToMm : public rclcpp::Node
{
public:
  explicit DepthToMm(const rclcpp::NodeOptions & options)
  : Node("depth_to_mm", options)
  {
    const auto output_topic = declare_parameter<std::string>("output_topic", "");
    if (output_topic.empty()) {
      throw std::runtime_error("parameter 'output_topic' must be set");
    }
    pub_ = image_transport::create_publisher(this, output_topic, rmw_qos_profile_default);
    sub_ = create_subscription<sensor_msgs::msg::Image>(
      "input", rclcpp::QoS(2),
      [this](sensor_msgs::msg::Image::ConstSharedPtr msg) { convert(*msg); });
  }

private:
  void convert(const sensor_msgs::msg::Image & in)
  {
    if (in.encoding != sensor_msgs::image_encodings::TYPE_32FC1) {
      RCLCPP_WARN_ONCE(get_logger(), "expected 32FC1 input, got %s: not converted", in.encoding.c_str());
      return;
    }
    sensor_msgs::msg::Image out;
    out.header = in.header;
    out.height = in.height;
    out.width = in.width;
    out.encoding = sensor_msgs::image_encodings::TYPE_16UC1;
    out.is_bigendian = false;
    out.step = in.width * sizeof(uint16_t);
    out.data.resize(static_cast<size_t>(out.step) * in.height);
    for (uint32_t r = 0; r < in.height; ++r) {
      const uint8_t * src = in.data.data() + static_cast<size_t>(r) * in.step;
      uint16_t * dst = reinterpret_cast<uint16_t *>(out.data.data() + static_cast<size_t>(r) * out.step);
      for (uint32_t c = 0; c < in.width; ++c) {
        float m;
        std::memcpy(&m, src + c * sizeof(float), sizeof(float));
        const float mm = m * 1000.0f;
        dst[c] = (std::isfinite(mm) && mm > 0.0f && mm < 65535.5f) ?
          static_cast<uint16_t>(std::lround(mm)) : 0;
      }
    }
    pub_.publish(out);
  }

  image_transport::Publisher pub_;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DepthToMm>(rclcpp::NodeOptions()));
  rclcpp::shutdown();
  return 0;
}
