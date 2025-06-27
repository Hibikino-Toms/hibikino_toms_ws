// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:srv/EndEffectorService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__STRUCT_H_
#define TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__STRUCT_H_

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

/// Struct defined in srv/EndEffectorService in the package toms_msg.
typedef struct toms_msg__srv__EndEffectorService_Request
{
  rosidl_runtime_c__String task;
} toms_msg__srv__EndEffectorService_Request;

// Struct for a sequence of toms_msg__srv__EndEffectorService_Request.
typedef struct toms_msg__srv__EndEffectorService_Request__Sequence
{
  toms_msg__srv__EndEffectorService_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__EndEffectorService_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/EndEffectorService in the package toms_msg.
typedef struct toms_msg__srv__EndEffectorService_Response
{
  bool task_done;
} toms_msg__srv__EndEffectorService_Response;

// Struct for a sequence of toms_msg__srv__EndEffectorService_Response.
typedef struct toms_msg__srv__EndEffectorService_Response__Sequence
{
  toms_msg__srv__EndEffectorService_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__EndEffectorService_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__STRUCT_H_
