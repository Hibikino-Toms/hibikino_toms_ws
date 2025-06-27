// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "toms_msg/msg/detail/tomato_pos__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace toms_msg
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void TomatoPos_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) toms_msg::msg::TomatoPos(_init);
}

void TomatoPos_fini_function(void * message_memory)
{
  auto typed_message = static_cast<toms_msg::msg::TomatoPos *>(message_memory);
  typed_message->~TomatoPos();
}

size_t size_function__TomatoPos__tomato_data(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<toms_msg::msg::TomatoData> *>(untyped_member);
  return member->size();
}

const void * get_const_function__TomatoPos__tomato_data(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<toms_msg::msg::TomatoData> *>(untyped_member);
  return &member[index];
}

void * get_function__TomatoPos__tomato_data(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<toms_msg::msg::TomatoData> *>(untyped_member);
  return &member[index];
}

void fetch_function__TomatoPos__tomato_data(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const toms_msg::msg::TomatoData *>(
    get_const_function__TomatoPos__tomato_data(untyped_member, index));
  auto & value = *reinterpret_cast<toms_msg::msg::TomatoData *>(untyped_value);
  value = item;
}

void assign_function__TomatoPos__tomato_data(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<toms_msg::msg::TomatoData *>(
    get_function__TomatoPos__tomato_data(untyped_member, index));
  const auto & value = *reinterpret_cast<const toms_msg::msg::TomatoData *>(untyped_value);
  item = value;
}

void resize_function__TomatoPos__tomato_data(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<toms_msg::msg::TomatoData> *>(untyped_member);
  member->resize(size);
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember TomatoPos_message_member_array[1] = {
  {
    "tomato_data",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<toms_msg::msg::TomatoData>(),  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg::msg::TomatoPos, tomato_data),  // bytes offset in struct
    nullptr,  // default value
    size_function__TomatoPos__tomato_data,  // size() function pointer
    get_const_function__TomatoPos__tomato_data,  // get_const(index) function pointer
    get_function__TomatoPos__tomato_data,  // get(index) function pointer
    fetch_function__TomatoPos__tomato_data,  // fetch(index, &value) function pointer
    assign_function__TomatoPos__tomato_data,  // assign(index, value) function pointer
    resize_function__TomatoPos__tomato_data  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers TomatoPos_message_members = {
  "toms_msg::msg",  // message namespace
  "TomatoPos",  // message name
  1,  // number of fields
  sizeof(toms_msg::msg::TomatoPos),
  TomatoPos_message_member_array,  // message members
  TomatoPos_init_function,  // function to initialize message memory (memory has to be allocated)
  TomatoPos_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t TomatoPos_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &TomatoPos_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace toms_msg


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<toms_msg::msg::TomatoPos>()
{
  return &::toms_msg::msg::rosidl_typesupport_introspection_cpp::TomatoPos_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, toms_msg, msg, TomatoPos)() {
  return &::toms_msg::msg::rosidl_typesupport_introspection_cpp::TomatoPos_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
