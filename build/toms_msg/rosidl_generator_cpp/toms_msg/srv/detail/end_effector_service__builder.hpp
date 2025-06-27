// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:srv/EndEffectorService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__BUILDER_HPP_
#define TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/srv/detail/end_effector_service__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_EndEffectorService_Request_task
{
public:
  Init_EndEffectorService_Request_task()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::srv::EndEffectorService_Request task(::toms_msg::srv::EndEffectorService_Request::_task_type arg)
  {
    msg_.task = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::EndEffectorService_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::EndEffectorService_Request>()
{
  return toms_msg::srv::builder::Init_EndEffectorService_Request_task();
}

}  // namespace toms_msg


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_EndEffectorService_Response_task_done
{
public:
  Init_EndEffectorService_Response_task_done()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::srv::EndEffectorService_Response task_done(::toms_msg::srv::EndEffectorService_Response::_task_done_type arg)
  {
    msg_.task_done = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::EndEffectorService_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::EndEffectorService_Response>()
{
  return toms_msg::srv::builder::Init_EndEffectorService_Response_task_done();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__BUILDER_HPP_
