// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:srv/SuctionCommand.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__STRUCT_H_
#define TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'command'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/SuctionCommand in the package toms_msg.
typedef struct toms_msg__srv__SuctionCommand_Request
{
  rosidl_runtime_c__String command;
} toms_msg__srv__SuctionCommand_Request;

// Struct for a sequence of toms_msg__srv__SuctionCommand_Request.
typedef struct toms_msg__srv__SuctionCommand_Request__Sequence
{
  toms_msg__srv__SuctionCommand_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__SuctionCommand_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'answer'
// already included above
// #include "rosidl_runtime_c/string.h"

/// Struct defined in srv/SuctionCommand in the package toms_msg.
typedef struct toms_msg__srv__SuctionCommand_Response
{
  rosidl_runtime_c__String answer;
} toms_msg__srv__SuctionCommand_Response;

// Struct for a sequence of toms_msg__srv__SuctionCommand_Response.
typedef struct toms_msg__srv__SuctionCommand_Response__Sequence
{
  toms_msg__srv__SuctionCommand_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__SuctionCommand_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__STRUCT_H_
