// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:srv/SuctionCommand.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__BUILDER_HPP_
#define TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/srv/detail/suction_command__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_SuctionCommand_Request_command
{
public:
  Init_SuctionCommand_Request_command()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::srv::SuctionCommand_Request command(::toms_msg::srv::SuctionCommand_Request::_command_type arg)
  {
    msg_.command = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::SuctionCommand_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::SuctionCommand_Request>()
{
  return toms_msg::srv::builder::Init_SuctionCommand_Request_command();
}

}  // namespace toms_msg


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_SuctionCommand_Response_answer
{
public:
  Init_SuctionCommand_Response_answer()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::srv::SuctionCommand_Response answer(::toms_msg::srv::SuctionCommand_Response::_answer_type arg)
  {
    msg_.answer = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::SuctionCommand_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::SuctionCommand_Response>()
{
  return toms_msg::srv::builder::Init_SuctionCommand_Response_answer();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__BUILDER_HPP_
