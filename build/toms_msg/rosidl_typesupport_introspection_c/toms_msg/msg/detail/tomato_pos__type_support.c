// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "toms_msg/msg/detail/tomato_pos__rosidl_typesupport_introspection_c.h"
#include "toms_msg/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "toms_msg/msg/detail/tomato_pos__functions.h"
#include "toms_msg/msg/detail/tomato_pos__struct.h"


// Include directives for member types
// Member `tomato_data`
#include "toms_msg/msg/tomato_data.h"
// Member `tomato_data`
#include "toms_msg/msg/detail/tomato_data__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  toms_msg__msg__TomatoPos__init(message_memory);
}

void toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_fini_function(void * message_memory)
{
  toms_msg__msg__TomatoPos__fini(message_memory);
}

size_t toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__size_function__TomatoPos__tomato_data(
  const void * untyped_member)
{
  const toms_msg__msg__TomatoData__Sequence * member =
    (const toms_msg__msg__TomatoData__Sequence *)(untyped_member);
  return member->size;
}

const void * toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__get_const_function__TomatoPos__tomato_data(
  const void * untyped_member, size_t index)
{
  const toms_msg__msg__TomatoData__Sequence * member =
    (const toms_msg__msg__TomatoData__Sequence *)(untyped_member);
  return &member->data[index];
}

void * toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__get_function__TomatoPos__tomato_data(
  void * untyped_member, size_t index)
{
  toms_msg__msg__TomatoData__Sequence * member =
    (toms_msg__msg__TomatoData__Sequence *)(untyped_member);
  return &member->data[index];
}

void toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__fetch_function__TomatoPos__tomato_data(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const toms_msg__msg__TomatoData * item =
    ((const toms_msg__msg__TomatoData *)
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__get_const_function__TomatoPos__tomato_data(untyped_member, index));
  toms_msg__msg__TomatoData * value =
    (toms_msg__msg__TomatoData *)(untyped_value);
  *value = *item;
}

void toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__assign_function__TomatoPos__tomato_data(
  void * untyped_member, size_t index, const void * untyped_value)
{
  toms_msg__msg__TomatoData * item =
    ((toms_msg__msg__TomatoData *)
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__get_function__TomatoPos__tomato_data(untyped_member, index));
  const toms_msg__msg__TomatoData * value =
    (const toms_msg__msg__TomatoData *)(untyped_value);
  *item = *value;
}

bool toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__resize_function__TomatoPos__tomato_data(
  void * untyped_member, size_t size)
{
  toms_msg__msg__TomatoData__Sequence * member =
    (toms_msg__msg__TomatoData__Sequence *)(untyped_member);
  toms_msg__msg__TomatoData__Sequence__fini(member);
  return toms_msg__msg__TomatoData__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_member_array[1] = {
  {
    "tomato_data",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__msg__TomatoPos, tomato_data),  // bytes offset in struct
    NULL,  // default value
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__size_function__TomatoPos__tomato_data,  // size() function pointer
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__get_const_function__TomatoPos__tomato_data,  // get_const(index) function pointer
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__get_function__TomatoPos__tomato_data,  // get(index) function pointer
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__fetch_function__TomatoPos__tomato_data,  // fetch(index, &value) function pointer
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__assign_function__TomatoPos__tomato_data,  // assign(index, value) function pointer
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__resize_function__TomatoPos__tomato_data  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_members = {
  "toms_msg__msg",  // message namespace
  "TomatoPos",  // message name
  1,  // number of fields
  sizeof(toms_msg__msg__TomatoPos),
  toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_member_array,  // message members
  toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_init_function,  // function to initialize message memory (memory has to be allocated)
  toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_type_support_handle = {
  0,
  &toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_toms_msg
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, msg, TomatoPos)() {
  toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, msg, TomatoData)();
  if (!toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_type_support_handle.typesupport_identifier) {
    toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &toms_msg__msg__TomatoPos__rosidl_typesupport_introspection_c__TomatoPos_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
