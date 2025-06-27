// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_POS__BUILDER_HPP_
#define TOMS_MSG__MSG__DETAIL__TOMATO_POS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/msg/detail/tomato_pos__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace msg
{

namespace builder
{

class Init_TomatoPos_tomato_data
{
public:
  Init_TomatoPos_tomato_data()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::msg::TomatoPos tomato_data(::toms_msg::msg::TomatoPos::_tomato_data_type arg)
  {
    msg_.tomato_data = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::msg::TomatoPos msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::msg::TomatoPos>()
{
  return toms_msg::msg::builder::Init_TomatoPos_tomato_data();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_POS__BUILDER_HPP_
