// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from toms_msg:srv/CartService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CART_SERVICE__TRAITS_HPP_
#define TOMS_MSG__SRV__DETAIL__CART_SERVICE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "toms_msg/srv/detail/cart_service__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const CartService_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: move_value
  {
    out << "move_value: ";
    rosidl_generator_traits::value_to_yaml(msg.move_value, out);
    out << ", ";
  }

  // member: pwm_value
  {
    out << "pwm_value: ";
    rosidl_generator_traits::value_to_yaml(msg.pwm_value, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const CartService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: move_value
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "move_value: ";
    rosidl_generator_traits::value_to_yaml(msg.move_value, out);
    out << "\n";
  }

  // member: pwm_value
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "pwm_value: ";
    rosidl_generator_traits::value_to_yaml(msg.pwm_value, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const CartService_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace toms_msg

namespace rosidl_generator_traits
{

[[deprecated("use toms_msg::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const toms_msg::srv::CartService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::CartService_Request & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::CartService_Request>()
{
  return "toms_msg::srv::CartService_Request";
}

template<>
inline const char * name<toms_msg::srv::CartService_Request>()
{
  return "toms_msg/srv/CartService_Request";
}

template<>
struct has_fixed_size<toms_msg::srv::CartService_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<toms_msg::srv::CartService_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<toms_msg::srv::CartService_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const CartService_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: move_result
  {
    out << "move_result: ";
    rosidl_generator_traits::value_to_yaml(msg.move_result, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const CartService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: move_result
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "move_result: ";
    rosidl_generator_traits::value_to_yaml(msg.move_result, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const CartService_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace toms_msg

namespace rosidl_generator_traits
{

[[deprecated("use toms_msg::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const toms_msg::srv::CartService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::CartService_Response & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::CartService_Response>()
{
  return "toms_msg::srv::CartService_Response";
}

template<>
inline const char * name<toms_msg::srv::CartService_Response>()
{
  return "toms_msg/srv/CartService_Response";
}

template<>
struct has_fixed_size<toms_msg::srv::CartService_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<toms_msg::srv::CartService_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<toms_msg::srv::CartService_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<toms_msg::srv::CartService>()
{
  return "toms_msg::srv::CartService";
}

template<>
inline const char * name<toms_msg::srv::CartService>()
{
  return "toms_msg/srv/CartService";
}

template<>
struct has_fixed_size<toms_msg::srv::CartService>
  : std::integral_constant<
    bool,
    has_fixed_size<toms_msg::srv::CartService_Request>::value &&
    has_fixed_size<toms_msg::srv::CartService_Response>::value
  >
{
};

template<>
struct has_bounded_size<toms_msg::srv::CartService>
  : std::integral_constant<
    bool,
    has_bounded_size<toms_msg::srv::CartService_Request>::value &&
    has_bounded_size<toms_msg::srv::CartService_Response>::value
  >
{
};

template<>
struct is_service<toms_msg::srv::CartService>
  : std::true_type
{
};

template<>
struct is_service_request<toms_msg::srv::CartService_Request>
  : std::true_type
{
};

template<>
struct is_service_response<toms_msg::srv::CartService_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // TOMS_MSG__SRV__DETAIL__CART_SERVICE__TRAITS_HPP_
