// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:srv/CartService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CART_SERVICE__STRUCT_H_
#define TOMS_MSG__SRV__DETAIL__CART_SERVICE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/CartService in the package toms_msg.
typedef struct toms_msg__srv__CartService_Request
{
  int16_t move_value;
  int16_t pwm_value;
} toms_msg__srv__CartService_Request;

// Struct for a sequence of toms_msg__srv__CartService_Request.
typedef struct toms_msg__srv__CartService_Request__Sequence
{
  toms_msg__srv__CartService_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__CartService_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/CartService in the package toms_msg.
typedef struct toms_msg__srv__CartService_Response
{
  float move_result;
} toms_msg__srv__CartService_Response;

// Struct for a sequence of toms_msg__srv__CartService_Response.
typedef struct toms_msg__srv__CartService_Response__Sequence
{
  toms_msg__srv__CartService_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__srv__CartService_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__CART_SERVICE__STRUCT_H_
