// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_POS__FUNCTIONS_H_
#define TOMS_MSG__MSG__DETAIL__TOMATO_POS__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "toms_msg/msg/rosidl_generator_c__visibility_control.h"

#include "toms_msg/msg/detail/tomato_pos__struct.h"

/// Initialize msg/TomatoPos message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * toms_msg__msg__TomatoPos
 * )) before or use
 * toms_msg__msg__TomatoPos__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__msg__TomatoPos__init(toms_msg__msg__TomatoPos * msg);

/// Finalize msg/TomatoPos message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__msg__TomatoPos__fini(toms_msg__msg__TomatoPos * msg);

/// Create msg/TomatoPos message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * toms_msg__msg__TomatoPos__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
toms_msg__msg__TomatoPos *
toms_msg__msg__TomatoPos__create();

/// Destroy msg/TomatoPos message.
/**
 * It calls
 * toms_msg__msg__TomatoPos__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__msg__TomatoPos__destroy(toms_msg__msg__TomatoPos * msg);

/// Check for msg/TomatoPos message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__msg__TomatoPos__are_equal(const toms_msg__msg__TomatoPos * lhs, const toms_msg__msg__TomatoPos * rhs);

/// Copy a msg/TomatoPos message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__msg__TomatoPos__copy(
  const toms_msg__msg__TomatoPos * input,
  toms_msg__msg__TomatoPos * output);

/// Initialize array of msg/TomatoPos messages.
/**
 * It allocates the memory for the number of elements and calls
 * toms_msg__msg__TomatoPos__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__msg__TomatoPos__Sequence__init(toms_msg__msg__TomatoPos__Sequence * array, size_t size);

/// Finalize array of msg/TomatoPos messages.
/**
 * It calls
 * toms_msg__msg__TomatoPos__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__msg__TomatoPos__Sequence__fini(toms_msg__msg__TomatoPos__Sequence * array);

/// Create array of msg/TomatoPos messages.
/**
 * It allocates the memory for the array and calls
 * toms_msg__msg__TomatoPos__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
toms_msg__msg__TomatoPos__Sequence *
toms_msg__msg__TomatoPos__Sequence__create(size_t size);

/// Destroy array of msg/TomatoPos messages.
/**
 * It calls
 * toms_msg__msg__TomatoPos__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__msg__TomatoPos__Sequence__destroy(toms_msg__msg__TomatoPos__Sequence * array);

/// Check for msg/TomatoPos message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__msg__TomatoPos__Sequence__are_equal(const toms_msg__msg__TomatoPos__Sequence * lhs, const toms_msg__msg__TomatoPos__Sequence * rhs);

/// Copy an array of msg/TomatoPos messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__msg__TomatoPos__Sequence__copy(
  const toms_msg__msg__TomatoPos__Sequence * input,
  toms_msg__msg__TomatoPos__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_POS__FUNCTIONS_H_
