// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:srv/ArmService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__ARM_SERVICE__STRUCT_H_
#define TOMS_MSG__SRV__DETAIL__ARM_SERVICE__STRUCT_H_

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
#include "rosidl_runtime_c/string.h"
// Member 'target'
#include "toms_msg/msg/detail/tomato_data__struct.h"

/// Struct defined in srv/ArmService in the package toms_msg.
typedef struct toms_msg__srv__ArmService_Request
{
  rosidl_runtime_c__String task;
  toms_msg__msg__TomatoData target;
} toms_msg__srv__ArmService_Request;

// Struct for a sequence of toms_msg__srv__ArmService_Request.
typedef struct toms_msg__srv__ArmService_Request__Sequence
{
  toms_msg__srv__ArmService_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__ArmService_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'tom_hight'
#include "std_msgs/msg/detail/int32__struct.h"

/// Struct defined in srv/ArmService in the package toms_msg.
typedef struct toms_msg__srv__ArmService_Response
{
  bool task_comp;
  std_msgs__msg__Int32 tom_hight;
} toms_msg__srv__ArmService_Response;

// Struct for a sequence of toms_msg__srv__ArmService_Response.
typedef struct toms_msg__srv__ArmService_Response__Sequence
{
  toms_msg__srv__ArmService_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__ArmService_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__ARM_SERVICE__STRUCT_H_
