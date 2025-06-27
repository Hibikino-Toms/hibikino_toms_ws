// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from toms_msg:msg/TomatoData.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_DATA__TRAITS_HPP_
#define TOMS_MSG__MSG__DETAIL__TOMATO_DATA__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "toms_msg/msg/detail/tomato_data__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace toms_msg
{

namespace msg
{

inline void to_flow_style_yaml(
  const TomatoData & msg,
  std::ostream & out)
{
  out << "{";
  // member: x
  {
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << ", ";
  }

  // member: y
  {
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << ", ";
  }

  // member: z
  {
    out << "z: ";
    rosidl_generator_traits::value_to_yaml(msg.z, out);
    out << ", ";
  }

  // member: approach_direction
  {
    out << "approach_direction: ";
    rosidl_generator_traits::value_to_yaml(msg.approach_direction, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const TomatoData & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << "\n";
  }

  // member: y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << "\n";
  }

  // member: z
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "z: ";
    rosidl_generator_traits::value_to_yaml(msg.z, out);
    out << "\n";
  }

  // member: approach_direction
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "approach_direction: ";
    rosidl_generator_traits::value_to_yaml(msg.approach_direction, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const TomatoData & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace toms_msg

namespace rosidl_generator_traits
{

[[deprecated("use toms_msg::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const toms_msg::msg::TomatoData & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::msg::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::msg::TomatoData & msg)
{
  return toms_msg::msg::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::msg::TomatoData>()
{
  return "toms_msg::msg::TomatoData";
}

template<>
inline const char * name<toms_msg::msg::TomatoData>()
{
  return "toms_msg/msg/TomatoData";
}

template<>
struct has_fixed_size<toms_msg::msg::TomatoData>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<toms_msg::msg::TomatoData>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<toms_msg::msg::TomatoData>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_DATA__TRAITS_HPP_
