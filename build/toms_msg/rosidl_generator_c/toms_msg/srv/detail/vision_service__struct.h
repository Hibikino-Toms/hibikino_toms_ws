// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:srv/VisionService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__VISION_SERVICE__STRUCT_H_
#define TOMS_MSG__SRV__DETAIL__VISION_SERVICE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'task'
// Member 'direction'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/VisionService in the package toms_msg.
typedef struct toms_msg__srv__VisionService_Request
{
  rosidl_runtime_c__String task;
  rosidl_runtime_c__String direction;
} toms_msg__srv__VisionService_Request;

// Struct for a sequence of toms_msg__srv__VisionService_Request.
typedef struct toms_msg__srv__VisionService_Request__Sequence
{
  toms_msg__srv__VisionService_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__VisionService_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'target_pos'
#include "toms_msg/msg/detail/tomato_pos__struct.h"

/// Struct defined in srv/VisionService in the package toms_msg.
typedef struct toms_msg__srv__VisionService_Response
{
  bool detect_check;
  toms_msg__msg__TomatoPos target_pos;
} toms_msg__srv__VisionService_Response;

// Struct for a sequence of toms_msg__srv__VisionService_Response.
typedef struct toms_msg__srv__VisionService_Response__Sequence
{
  toms_msg__srv__VisionService_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__VisionService_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__VISION_SERVICE__STRUCT_H_
