// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from toms_msg:srv/VisionService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__VISION_SERVICE__TRAITS_HPP_
#define TOMS_MSG__SRV__DETAIL__VISION_SERVICE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "toms_msg/srv/detail/vision_service__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const VisionService_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: task
  {
    out << "task: ";
    rosidl_generator_traits::value_to_yaml(msg.task, out);
    out << ", ";
  }

  // member: direction
  {
    out << "direction: ";
    rosidl_generator_traits::value_to_yaml(msg.direction, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const VisionService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: task
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "task: ";
    rosidl_generator_traits::value_to_yaml(msg.task, out);
    out << "\n";
  }

  // member: direction
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "direction: ";
    rosidl_generator_traits::value_to_yaml(msg.direction, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const VisionService_Request & msg, bool use_flow_style = false)
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
  const toms_msg::srv::VisionService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::VisionService_Request & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::VisionService_Request>()
{
  return "toms_msg::srv::VisionService_Request";
}

template<>
inline const char * name<toms_msg::srv::VisionService_Request>()
{
  return "toms_msg/srv/VisionService_Request";
}

template<>
struct has_fixed_size<toms_msg::srv::VisionService_Request>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<toms_msg::srv::VisionService_Request>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<toms_msg::srv::VisionService_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'target_pos'
#include "toms_msg/msg/detail/tomato_pos__traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const VisionService_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: detect_check
  {
    out << "detect_check: ";
    rosidl_generator_traits::value_to_yaml(msg.detect_check, out);
    out << ", ";
  }

  // member: target_pos
  {
    out << "target_pos: ";
    to_flow_style_yaml(msg.target_pos, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const VisionService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: detect_check
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "detect_check: ";
    rosidl_generator_traits::value_to_yaml(msg.detect_check, out);
    out << "\n";
  }

  // member: target_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "target_pos:\n";
    to_block_style_yaml(msg.target_pos, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const VisionService_Response & msg, bool use_flow_style = false)
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
  const toms_msg::srv::VisionService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::VisionService_Response & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::VisionService_Response>()
{
  return "toms_msg::srv::VisionService_Response";
}

template<>
inline const char * name<toms_msg::srv::VisionService_Response>()
{
  return "toms_msg/srv/VisionService_Response";
}

template<>
struct has_fixed_size<toms_msg::srv::VisionService_Response>
  : std::integral_constant<bool, has_fixed_size<toms_msg::msg::TomatoPos>::value> {};

template<>
struct has_bounded_size<toms_msg::srv::VisionService_Response>
  : std::integral_constant<bool, has_bounded_size<toms_msg::msg::TomatoPos>::value> {};

template<>
struct is_message<toms_msg::srv::VisionService_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<toms_msg::srv::VisionService>()
{
  return "toms_msg::srv::VisionService";
}

template<>
inline const char * name<toms_msg::srv::VisionService>()
{
  return "toms_msg/srv/VisionService";
}

template<>
struct has_fixed_size<toms_msg::srv::VisionService>
  : std::integral_constant<
    bool,
    has_fixed_size<toms_msg::srv::VisionService_Request>::value &&
    has_fixed_size<toms_msg::srv::VisionService_Response>::value
  >
{
};

template<>
struct has_bounded_size<toms_msg::srv::VisionService>
  : std::integral_constant<
    bool,
    has_bounded_size<toms_msg::srv::VisionService_Request>::value &&
    has_bounded_size<toms_msg::srv::VisionService_Response>::value
  >
{
};

template<>
struct is_service<toms_msg::srv::VisionService>
  : std::true_type
{
};

template<>
struct is_service_request<toms_msg::srv::VisionService_Request>
  : std::true_type
{
};

template<>
struct is_service_response<toms_msg::srv::VisionService_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // TOMS_MSG__SRV__DETAIL__VISION_SERVICE__TRAITS_HPP_
