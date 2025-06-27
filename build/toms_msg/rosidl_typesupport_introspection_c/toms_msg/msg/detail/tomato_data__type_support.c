// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from toms_msg:msg/TomatoData.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "toms_msg/msg/detail/tomato_data__rosidl_typesupport_introspection_c.h"
#include "toms_msg/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "toms_msg/msg/detail/tomato_data__functions.h"
#include "toms_msg/msg/detail/tomato_data__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  toms_msg__msg__TomatoData__init(message_memory);
}

void toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_fini_function(void * message_memory)
{
  toms_msg__msg__TomatoData__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_member_array[4] = {
  {
    "x",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT16,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__msg__TomatoData, x),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "y",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT16,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__msg__TomatoData, y),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "z",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT16,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__msg__TomatoData, z),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "approach_direction",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT16,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__msg__TomatoData, approach_direction),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_members = {
  "toms_msg__msg",  // message namespace
  "TomatoData",  // message name
  4,  // number of fields
  sizeof(toms_msg__msg__TomatoData),
  toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_member_array,  // message members
  toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_init_function,  // function to initialize message memory (memory has to be allocated)
  toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_type_support_handle = {
  0,
  &toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_toms_msg
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, msg, TomatoData)() {
  if (!toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_type_support_handle.typesupport_identifier) {
    toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &toms_msg__msg__TomatoData__rosidl_typesupport_introspection_c__TomatoData_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
