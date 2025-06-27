// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from toms_msg:msg/TomatoData.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_DATA__STRUCT_H_
#define TOMS_MSG__MSG__DETAIL__TOMATO_DATA__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/TomatoData in the package toms_msg.
typedef struct toms_msg__msg__TomatoData
{
  int16_t x;
  int16_t y;
  int16_t z;
  int16_t approach_direction;
} toms_msg__msg__TomatoData;

// Struct for a sequence of toms_msg__msg__TomatoData.
typedef struct toms_msg__msg__TomatoData__Sequence
{
  toms_msg__msg__TomatoData * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} toms_msg__msg__TomatoData__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_DATA__STRUCT_H_
