// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_POS__STRUCT_H_
#define TOMS_MSG__MSG__DETAIL__TOMATO_POS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'tomato_data'
#include "toms_msg/msg/detail/tomato_data__struct.h"

/// Struct defined in msg/TomatoPos in the package toms_msg.
typedef struct toms_msg__msg__TomatoPos
{
  toms_msg__msg__TomatoData__Sequence tomato_data;
} toms_msg__msg__TomatoPos;

// Struct for a sequence of toms_msg__msg__TomatoPos.
typedef struct toms_msg__msg__TomatoPos__Sequence
{
  toms_msg__msg__TomatoPos * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__msg__TomatoPos__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_POS__STRUCT_H_
