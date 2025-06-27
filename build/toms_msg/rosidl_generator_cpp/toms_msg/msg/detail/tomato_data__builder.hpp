// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:msg/TomatoData.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_DATA__BUILDER_HPP_
#define TOMS_MSG__MSG__DETAIL__TOMATO_DATA__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/msg/detail/tomato_data__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace msg
{

namespace builder
{

class Init_TomatoData_approach_direction
{
public:
  explicit Init_TomatoData_approach_direction(::toms_msg::msg::TomatoData & msg)
  : msg_(msg)
  {}
  ::toms_msg::msg::TomatoData approach_direction(::toms_msg::msg::TomatoData::_approach_direction_type arg)
  {
    msg_.approach_direction = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::msg::TomatoData msg_;
};

class Init_TomatoData_z
{
public:
  explicit Init_TomatoData_z(::toms_msg::msg::TomatoData & msg)
  : msg_(msg)
  {}
  Init_TomatoData_approach_direction z(::toms_msg::msg::TomatoData::_z_type arg)
  {
    msg_.z = std::move(arg);
    return Init_TomatoData_approach_direction(msg_);
  }

private:
  ::toms_msg::msg::TomatoData msg_;
};

class Init_TomatoData_y
{
public:
  explicit Init_TomatoData_y(::toms_msg::msg::TomatoData & msg)
  : msg_(msg)
  {}
  Init_TomatoData_z y(::toms_msg::msg::TomatoData::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_TomatoData_z(msg_);
  }

private:
  ::toms_msg::msg::TomatoData msg_;
};

class Init_TomatoData_x
{
public:
  Init_TomatoData_x()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_TomatoData_y x(::toms_msg::msg::TomatoData::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_TomatoData_y(msg_);
  }

private:
  ::toms_msg::msg::TomatoData msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::msg::TomatoData>()
{
  return toms_msg::msg::builder::Init_TomatoData_x();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_DATA__BUILDER_HPP_
