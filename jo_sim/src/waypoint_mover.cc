// Gazebo system: moves its model along waypoints, on sim time (D3, dynamic obstacles).
//
// The model is teleported every step (WorldPoseCmd), so it is kinematic: contacts do not move it
// (it pushes whatever it walks into), and without yield_to its motion is a pure function of sim time. Unlike a skinned <actor>, it is an ordinary model with
// visuals, so the RGL lidar, the cameras and the physics all see it.
//
//   <model name="walker"> ... (non-static, links with <gravity>false</gravity>)
//     <plugin filename="jo_sim_waypoint_mover" name="jo_sim::WaypointMover">
//       <speed>0.8</speed>          <!-- [m/s] along the path -->
//       <mode>pingpong</mode>       <!-- pingpong | loop (back to the first waypoint) | once -->
//       <pause>1.0</pause>          <!-- [s] at each waypoint (turns towards the next leg meanwhile) -->
//       <delay>0</delay>            <!-- [s, sim] before starting -->
//       <face_motion>true</face_motion>
//       <yield_to>jo</yield_to>     <!-- optional: stop while this model is within yield_distance -->
//       <yield_distance>1.0</yield_distance>  <!-- [m] ahead, in the walking direction -->
//       <waypoint>3 -2</waypoint>   <!-- x y [z]; z = the model's initial z if omitted -->
//       <waypoint>3 2</waypoint>
//     </plugin>
//   </model>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <sstream>
#include <string>
#include <vector>

#include <gz/common/Console.hh>
#include <gz/math/Pose3.hh>
#include <gz/plugin/Register.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <sdf/Element.hh>

namespace jo_sim
{

class WaypointMover : public gz::sim::System,
                      public gz::sim::ISystemConfigure,
                      public gz::sim::ISystemPreUpdate
{
public:
  void Configure(const gz::sim::Entity &entity, const std::shared_ptr<const sdf::Element> &sdf,
                 gz::sim::EntityComponentManager &ecm, gz::sim::EventManager &) override
  {
    model_ = gz::sim::Model(entity);
    if (!model_.Valid(ecm)) {
      gzerr << "[WaypointMover] must be attached to a model\n";
      return;
    }
    const auto name = model_.Name(ecm);
    const double speed = sdf->Get<double>("speed", 0.8).first;
    const double pause = sdf->Get<double>("pause", 0.0).first;
    const std::string mode = sdf->Get<std::string>("mode", "pingpong").first;
    delay_ = sdf->Get<double>("delay", 0.0).first;
    const bool face = sdf->Get<bool>("face_motion", true).first;
    yield_to_ = sdf->Get<std::string>("yield_to", "").first;
    yield_distance_ = sdf->Get<double>("yield_distance", 1.0).first;
    once_ = mode == "once";
    if (mode != "pingpong" && mode != "loop" && !once_) {
      gzerr << "[WaypointMover] " << name << ": mode '" << mode << "' (pingpong | loop | once)\n";
      return;
    }
    if (speed <= 0) {
      gzerr << "[WaypointMover] " << name << ": speed must be > 0\n";
      return;
    }

    const auto initial = gz::sim::worldPose(entity, ecm);
    std::vector<gz::math::Vector3d> pts;
    auto *el = const_cast<sdf::Element *>(sdf.get());
    for (auto w = el->HasElement("waypoint") ? el->GetElement("waypoint") : nullptr; w;
         w = w->GetNextElement("waypoint")) {
      std::istringstream in(w->Get<std::string>());
      double x, y, z = initial.Pos().Z();
      if (!(in >> x >> y)) {
        gzerr << "[WaypointMover] " << name << ": bad waypoint '" << w->Get<std::string>() << "'\n";
        return;
      }
      in >> z;
      pts.emplace_back(x, y, z);
    }
    if (pts.size() < 2) {
      gzerr << "[WaypointMover] " << name << ": needs at least 2 waypoints\n";
      return;
    }
    std::vector<gz::math::Vector3d> path = pts;
    if (mode == "pingpong") {
      path.insert(path.end(), pts.rbegin() + 1, pts.rend());
    } else if (mode == "loop") {
      path.push_back(pts.front());
    }

    // Keyframes: move along each leg facing it, then turn towards the next leg during the pause
    const double yaw0 = initial.Rot().Yaw();
    auto heading = [&](size_t i) {
      const auto d = path[i + 1] - path[i];
      return face ? std::atan2(d.Y(), d.X()) : yaw0;
    };
    double t = 0.0;
    for (size_t i = 0; i + 1 < path.size(); ++i) {
      const double h = heading(i);
      frames_.push_back({t, path[i], h});
      t += path[i].Distance(path[i + 1]) / speed;
      frames_.push_back({t, path[i + 1], h});
      const bool last = i + 2 == path.size();
      if (pause > 0 && !(last && once_)) {
        t += pause;
        frames_.push_back({t, path[i + 1], last ? heading(0) : heading(i + 1)});
      }
    }
    period_ = t;
    gzmsg << "[WaypointMover] " << name << ": " << pts.size() << " waypoints, " << mode << ", period "
          << period_ << " s\n";
  }

  void PreUpdate(const gz::sim::UpdateInfo &info, gz::sim::EntityComponentManager &ecm) override
  {
    if (info.paused || frames_.empty()) {
      return;
    }
    // Path time: advances with sim time after the delay, and stands still while yielding
    const double now = std::chrono::duration<double>(info.simTime).count();
    const double dt = last_ < 0 ? 0.0 : std::max(0.0, now - last_);
    last_ = now;
    if (now >= delay_ && !Yielding(ecm)) {
      tau_ += now - dt < delay_ ? now - delay_ : dt;
    }
    const double t = once_ ? std::min(tau_, period_) : std::fmod(tau_, period_);

    size_t i = 0;
    while (i + 2 < frames_.size() && frames_[i + 1].t <= t) {
      ++i;
    }
    const auto &a = frames_[i], &b = frames_[i + 1];
    const double s = b.t > a.t ? std::clamp((t - a.t) / (b.t - a.t), 0.0, 1.0) : 1.0;
    const auto pos = a.pos + (b.pos - a.pos) * s;
    const double dyaw = std::atan2(std::sin(b.yaw - a.yaw), std::cos(b.yaw - a.yaw));
    model_.SetWorldPoseCmd(ecm, gz::math::Pose3d(pos, gz::math::Quaterniond(0, 0, a.yaw + dyaw * s)));
    pos_ = pos;
    dir_ = b.pos - a.pos;
  }

private:
  // True while the yield_to model is within yield_distance and ahead (in the walking direction)
  bool Yielding(const gz::sim::EntityComponentManager &ecm)
  {
    if (yield_to_.empty() || dir_.Length() < 1e-6) {
      return false;
    }
    if (other_ == gz::sim::kNullEntity) {
      other_ = ecm.EntityByComponents(gz::sim::components::Name(yield_to_), gz::sim::components::Model());
      if (other_ == gz::sim::kNullEntity) {
        return false;
      }
    }
    auto rel = gz::sim::worldPose(other_, ecm).Pos() - pos_;
    rel.Z(0);
    auto dir = dir_;
    dir.Z(0);
    return rel.Length() < yield_distance_ && rel.Dot(dir) > 0;
  }

  struct Frame
  {
    double t;
    gz::math::Vector3d pos;
    double yaw;
  };
  gz::sim::Model model_{gz::sim::kNullEntity};
  std::vector<Frame> frames_;
  double period_{0.0};
  double delay_{0.0};
  bool once_{false};
  std::string yield_to_;
  double yield_distance_{1.0};
  gz::sim::Entity other_{gz::sim::kNullEntity};
  gz::math::Vector3d pos_, dir_;
  double tau_{0.0};
  double last_{-1.0};
};

}  // namespace jo_sim

GZ_ADD_PLUGIN(jo_sim::WaypointMover, gz::sim::System, jo_sim::WaypointMover::ISystemConfigure,
              jo_sim::WaypointMover::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(jo_sim::WaypointMover, "jo_sim::WaypointMover")
