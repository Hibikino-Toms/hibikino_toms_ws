// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:srv/VisionService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__VISION_SERVICE__BUILDER_HPP_
#define TOMS_MSG__SRV__DETAIL__VISION_SERVICE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/srv/detail/vision_service__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_VisionService_Request_direction
{
public:
  explicit Init_VisionService_Request_direction(::toms_msg::srv::VisionService_Request & msg)
  : msg_(msg)
  {}
  ::toms_msg::srv::VisionService_Request direction(::toms_msg::srv::VisionService_Request::_direction_type arg)
  {
    msg_.direction = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::VisionService_Request msg_;
};

class Init_VisionService_Request_task
{
public:
  Init_VisionService_Request_task()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_VisionService_Request_direction task(::toms_msg::srv::VisionService_Request::_task_type arg)
  {
    msg_.task = std::move(arg);
    return Init_VisionService_Request_direction(msg_);
  }

private:
  ::toms_msg::srv::VisionService_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::VisionService_Request>()
{
  return toms_msg::srv::builder::Init_VisionService_Request_task();
}

}  // namespace toms_msg


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_VisionService_Response_target_pos
{
public:
  explicit Init_VisionService_Response_target_pos(::toms_msg::srv::VisionService_Response & msg)
  : msg_(msg)
  {}
  ::toms_msg::srv::VisionService_Response target_pos(::toms_msg::srv::VisionService_Response::_target_pos_type arg)
  {
    msg_.target_pos = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::VisionService_Response msg_;
};

class Init_VisionService_Response_detect_check
{
public:
  Init_VisionService_Response_detect_check()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_VisionService_Response_target_pos detect_check(::toms_msg::srv::VisionService_Response::_detect_check_type arg)
  {
    msg_.detect_check = std::move(arg);
    return Init_VisionService_Response_target_pos(msg_);
  }

private:
  ::toms_msg::srv::VisionService_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::VisionService_Response>()
{
  return toms_msg::srv::builder::Init_VisionService_Response_detect_check();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__VISION_SERVICE__BUILDER_HPP_
