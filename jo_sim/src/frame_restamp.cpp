// Republishes a PointCloud2 with a different header.frame_id.
//
// Gazebo's rgbd_camera stamps every output with the same <gz_frame_id>. Images must carry the
// optical frame (as the RealSense driver does, RTAB-Map relies on it), but Gazebo builds the point
// cloud in the X-forward camera convention, so the cloud is republished in the non-optical frame.
//
// Topics: ~/input -> ~/output (remap them). Parameter: frame_id.
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"

class FrameRestamp : public rclcpp::Node
{
public:
  explicit FrameRestamp(const rclcpp::NodeOptions & options)
  : Node("frame_restamp", options)
  {
    frame_id_ = declare_parameter<std::string>("frame_id", "");
    if (frame_id_.empty()) {
      throw std::runtime_error("parameter 'frame_id' must be set");
    }
    pub_ = create_publisher<sensor_msgs::msg::PointCloud2>("output", rclcpp::QoS(10));
    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      // Reliable: an RGB-D cloud is ~10 MB, best effort loses fragments and never delivers it
      "input", rclcpp::QoS(2),
      [this](sensor_msgs::msg::PointCloud2::UniquePtr msg) {
        msg->header.frame_id = frame_id_;
        pub_->publish(std::move(msg));
      });
  }

private:
  std::string frame_id_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FrameRestamp>(rclcpp::NodeOptions()));
  rclcpp::shutdown();
  return 0;
}
