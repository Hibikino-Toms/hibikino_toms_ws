// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from toms_msg:srv/ArmService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__ARM_SERVICE__TRAITS_HPP_
#define TOMS_MSG__SRV__DETAIL__ARM_SERVICE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "toms_msg/srv/detail/arm_service__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'target'
#include "toms_msg/msg/detail/tomato_data__traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const ArmService_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: task
  {
    out << "task: ";
    rosidl_generator_traits::value_to_yaml(msg.task, out);
    out << ", ";
  }

  // member: target
  {
    out << "target: ";
    to_flow_style_yaml(msg.target, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ArmService_Request & msg,
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

  // member: target
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "target:\n";
    to_block_style_yaml(msg.target, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ArmService_Request & msg, bool use_flow_style = false)
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
  const toms_msg::srv::ArmService_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::ArmService_Request & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::ArmService_Request>()
{
  return "toms_msg::srv::ArmService_Request";
}

template<>
inline const char * name<toms_msg::srv::ArmService_Request>()
{
  return "toms_msg/srv/ArmService_Request";
}

template<>
struct has_fixed_size<toms_msg::srv::ArmService_Request>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<toms_msg::srv::ArmService_Request>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<toms_msg::srv::ArmService_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'tom_hight'
#include "std_msgs/msg/detail/int32__traits.hpp"

namespace toms_msg
{

namespace srv
{

inline void to_flow_style_yaml(
  const ArmService_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: task_comp
  {
    out << "task_comp: ";
    rosidl_generator_traits::value_to_yaml(msg.task_comp, out);
    out << ", ";
  }

  // member: tom_hight
  {
    out << "tom_hight: ";
    to_flow_style_yaml(msg.tom_hight, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ArmService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: task_comp
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "task_comp: ";
    rosidl_generator_traits::value_to_yaml(msg.task_comp, out);
    out << "\n";
  }

  // member: tom_hight
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "tom_hight:\n";
    to_block_style_yaml(msg.tom_hight, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ArmService_Response & msg, bool use_flow_style = false)
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
  const toms_msg::srv::ArmService_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::srv::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::srv::ArmService_Response & msg)
{
  return toms_msg::srv::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::srv::ArmService_Response>()
{
  return "toms_msg::srv::ArmService_Response";
}

template<>
inline const char * name<toms_msg::srv::ArmService_Response>()
{
  return "toms_msg/srv/ArmService_Response";
}

template<>
struct has_fixed_size<toms_msg::srv::ArmService_Response>
  : std::integral_constant<bool, has_fixed_size<std_msgs::msg::Int32>::value> {};

template<>
struct has_bounded_size<toms_msg::srv::ArmService_Response>
  : std::integral_constant<bool, has_bounded_size<std_msgs::msg::Int32>::value> {};

template<>
struct is_message<toms_msg::srv::ArmService_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<toms_msg::srv::ArmService>()
{
  return "toms_msg::srv::ArmService";
}

template<>
inline const char * name<toms_msg::srv::ArmService>()
{
  return "toms_msg/srv/ArmService";
}

template<>
struct has_fixed_size<toms_msg::srv::ArmService>
  : std::integral_constant<
    bool,
    has_fixed_size<toms_msg::srv::ArmService_Request>::value &&
    has_fixed_size<toms_msg::srv::ArmService_Response>::value
  >
{
};

template<>
struct has_bounded_size<toms_msg::srv::ArmService>
  : std::integral_constant<
    bool,
    has_bounded_size<toms_msg::srv::ArmService_Request>::value &&
    has_bounded_size<toms_msg::srv::ArmService_Response>::value
  >
{
};

template<>
struct is_service<toms_msg::srv::ArmService>
  : std::true_type
{
};

template<>
struct is_service_request<toms_msg::srv::ArmService_Request>
  : std::true_type
{
};

template<>
struct is_service_response<toms_msg::srv::ArmService_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // TOMS_MSG__SRV__DETAIL__ARM_SERVICE__TRAITS_HPP_
