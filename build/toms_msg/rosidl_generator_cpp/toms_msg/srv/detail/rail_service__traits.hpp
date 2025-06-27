// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from toms_msg:srv/RailService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__RAIL_SERVICE__TRAITS_HPP_
#define TOMS_MSG__SRV__DETAIL__RAIL_SERVICE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "toms_msg/srv/detail/rail_service__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const RailService_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: req_dir
  {
    out << "req_dir: ";
    rosidl_generator_traits::value_to_yaml(msg.req_dir, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const RailService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: req_dir
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "req_dir: ";
    rosidl_generator_traits::value_to_yaml(msg.req_dir, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const RailService_Request & msg, bool use_flow_style = false)
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
  const toms_msg::srv::RailService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::RailService_Request & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::RailService_Request>()
{
  return "toms_msg::srv::RailService_Request";
}

template<>
inline const char * name<toms_msg::srv::RailService_Request>()
{
  return "toms_msg/srv/RailService_Request";
}

template<>
struct has_fixed_size<toms_msg::srv::RailService_Request>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<toms_msg::srv::RailService_Request>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<toms_msg::srv::RailService_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'pulse'
#include "std_msgs/msg/detail/int32__traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const RailService_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: res_dir
  {
    out << "res_dir: ";
    rosidl_generator_traits::value_to_yaml(msg.res_dir, out);
    out << ", ";
  }

  // member: pulse
  {
    out << "pulse: ";
    to_flow_style_yaml(msg.pulse, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const RailService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: res_dir
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "res_dir: ";
    rosidl_generator_traits::value_to_yaml(msg.res_dir, out);
    out << "\n";
  }

  // member: pulse
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "pulse:\n";
    to_block_style_yaml(msg.pulse, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const RailService_Response & msg, bool use_flow_style = false)
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
  const toms_msg::srv::RailService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::RailService_Response & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::RailService_Response>()
{
  return "toms_msg::srv::RailService_Response";
}

template<>
inline const char * name<toms_msg::srv::RailService_Response>()
{
  return "toms_msg/srv/RailService_Response";
}

template<>
struct has_fixed_size<toms_msg::srv::RailService_Response>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<toms_msg::srv::RailService_Response>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<toms_msg::srv::RailService_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<toms_msg::srv::RailService>()
{
  return "toms_msg::srv::RailService";
}

template<>
inline const char * name<toms_msg::srv::RailService>()
{
  return "toms_msg/srv/RailService";
}

template<>
struct has_fixed_size<toms_msg::srv::RailService>
  : std::integral_constant<
    bool,
    has_fixed_size<toms_msg::srv::RailService_Request>::value &&
    has_fixed_size<toms_msg::srv::RailService_Response>::value
  >
{
};

template<>
struct has_bounded_size<toms_msg::srv::RailService>
  : std::integral_constant<
    bool,
    has_bounded_size<toms_msg::srv::RailService_Request>::value &&
    has_bounded_size<toms_msg::srv::RailService_Response>::value
  >
{
};

template<>
struct is_service<toms_msg::srv::RailService>
  : std::true_type
{
};

template<>
struct is_service_request<toms_msg::srv::RailService_Request>
  : std::true_type
{
};

template<>
struct is_service_response<toms_msg::srv::RailService_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // TOMS_MSG__SRV__DETAIL__RAIL_SERVICE__TRAITS_HPP_
