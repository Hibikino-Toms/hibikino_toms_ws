// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:srv/CartService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CART_SERVICE__BUILDER_HPP_
#define TOMS_MSG__SRV__DETAIL__CART_SERVICE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/srv/detail/cart_service__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_CartService_Request_pwm_value
{
public:
  explicit Init_CartService_Request_pwm_value(::toms_msg::srv::CartService_Request & msg)
  : msg_(msg)
  {}
  ::toms_msg::srv::CartService_Request pwm_value(::toms_msg::srv::CartService_Request::_pwm_value_type arg)
  {
    msg_.pwm_value = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::CartService_Request msg_;
};

class Init_CartService_Request_move_value
{
public:
  Init_CartService_Request_move_value()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_CartService_Request_pwm_value move_value(::toms_msg::srv::CartService_Request::_move_value_type arg)
  {
    msg_.move_value = std::move(arg);
    return Init_CartService_Request_pwm_value(msg_);
  }

private:
  ::toms_msg::srv::CartService_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::CartService_Request>()
{
  return toms_msg::srv::builder::Init_CartService_Request_move_value();
}

}  // namespace toms_msg


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_CartService_Response_move_result
{
public:
  Init_CartService_Response_move_result()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::srv::CartService_Response move_result(::toms_msg::srv::CartService_Response::_move_result_type arg)
  {
    msg_.move_result = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::CartService_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::CartService_Response>()
{
  return toms_msg::srv::builder::Init_CartService_Response_move_result();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__CART_SERVICE__BUILDER_HPP_
