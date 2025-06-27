// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_POS__TRAITS_HPP_
#define TOMS_MSG__MSG__DETAIL__TOMATO_POS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "toms_msg/msg/detail/tomato_pos__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'tomato_data'
#include "toms_msg/msg/detail/tomato_data__traits.hpp"

namespace toms_msg
{

namespace msg
{

inline void to_flow_style_yaml(
  const TomatoPos & msg,
  std::ostream & out)
{
  out << "{";
  // member: tomato_data
  {
    if (msg.tomato_data.size() == 0) {
      out << "tomato_data: []";
    } else {
      out << "tomato_data: [";
      size_t pending_items = msg.tomato_data.size();
      for (auto item : msg.tomato_data) {
        to_flow_style_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const TomatoPos & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: tomato_data
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.tomato_data.size() == 0) {
      out << "tomato_data: []\n";
    } else {
      out << "tomato_data:\n";
      for (auto item : msg.tomato_data) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "-\n";
        to_block_style_yaml(item, out, indentation + 2);
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const TomatoPos & msg, bool use_flow_style = false)
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
  const toms_msg::msg::TomatoPos & msg,
  std::ostream & out, size_t indentation = 0)
{
  toms_msg::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use toms_msg::msg::to_yaml() instead")]]
inline std::string to_yaml(const toms_msg::msg::TomatoPos & msg)
{
  return toms_msg::msg::to_yaml(msg);
}

template<>
inline const char * data_type<toms_msg::msg::TomatoPos>()
{
  return "toms_msg::msg::TomatoPos";
}

template<>
inline const char * name<toms_msg::msg::TomatoPos>()
{
  return "toms_msg/msg/TomatoPos";
}

template<>
struct has_fixed_size<toms_msg::msg::TomatoPos>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<toms_msg::msg::TomatoPos>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<toms_msg::msg::TomatoPos>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_POS__TRAITS_HPP_
