// NOLINT: This file starts with a BOM since it contain non-ASCII characters
// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:srv/RailService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__RAIL_SERVICE__STRUCT_H_
#define TOMS_MSG__SRV__DETAIL__RAIL_SERVICE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'req_dir'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/RailService in the package toms_msg.
typedef struct toms_msg__srv__RailService_Request
{
  /// 移動コマンド
  rosidl_runtime_c__String req_dir;
} toms_msg__srv__RailService_Request;

// Struct for a sequence of toms_msg__srv__RailService_Request.
typedef struct toms_msg__srv__RailService_Request__Sequence
{
  toms_msg__srv__RailService_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__RailService_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'res_dir'
// already included above
// #include "rosidl_runtime_c/string.h"
// Member 'pulse'
#include "std_msgs/msg/detail/int32__struct.h"

/// Struct defined in srv/RailService in the package toms_msg.
typedef struct toms_msg__srv__RailService_Response
{
  /// 現在の移動方向 ("forward" または "back")
  rosidl_runtime_c__String res_dir;
  std_msgs__msg__Int32 pulse;
} toms_msg__srv__RailService_Response;

// Struct for a sequence of toms_msg__srv__RailService_Response.
typedef struct toms_msg__srv__RailService_Response__Sequence
{
  toms_msg__srv__RailService_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__RailService_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__RAIL_SERVICE__STRUCT_H_
