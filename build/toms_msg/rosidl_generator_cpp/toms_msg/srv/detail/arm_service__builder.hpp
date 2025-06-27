// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:srv/ArmService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__ARM_SERVICE__BUILDER_HPP_
#define TOMS_MSG__SRV__DETAIL__ARM_SERVICE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/srv/detail/arm_service__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_ArmService_Request_target
{
public:
  explicit Init_ArmService_Request_target(::toms_msg::srv::ArmService_Request & msg)
  : msg_(msg)
  {}
  ::toms_msg::srv::ArmService_Request target(::toms_msg::srv::ArmService_Request::_target_type arg)
  {
    msg_.target = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::ArmService_Request msg_;
};

class Init_ArmService_Request_task
{
public:
  Init_ArmService_Request_task()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_ArmService_Request_target task(::toms_msg::srv::ArmService_Request::_task_type arg)
  {
    msg_.task = std::move(arg);
    return Init_ArmService_Request_target(msg_);
  }

private:
  ::toms_msg::srv::ArmService_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::ArmService_Request>()
{
  return toms_msg::srv::builder::Init_ArmService_Request_task();
}

}  // namespace toms_msg


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_ArmService_Response_tom_hight
{
public:
  explicit Init_ArmService_Response_tom_hight(::toms_msg::srv::ArmService_Response & msg)
  : msg_(msg)
  {}
  ::toms_msg::srv::ArmService_Response tom_hight(::toms_msg::srv::ArmService_Response::_tom_hight_type arg)
  {
    msg_.tom_hight = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::ArmService_Response msg_;
};

class Init_ArmService_Response_task_comp
{
public:
  Init_ArmService_Response_task_comp()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_ArmService_Response_tom_hight task_comp(::toms_msg::srv::ArmService_Response::_task_comp_type arg)
  {
    msg_.task_comp = std::move(arg);
    return Init_ArmService_Response_tom_hight(msg_);
  }

private:
  ::toms_msg::srv::ArmService_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::ArmService_Response>()
{
  return toms_msg::srv::builder::Init_ArmService_Response_task_comp();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__ARM_SERVICE__BUILDER_HPP_
