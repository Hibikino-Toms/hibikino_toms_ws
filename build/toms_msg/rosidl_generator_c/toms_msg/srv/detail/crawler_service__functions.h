// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from toms_msg:srv/CrawlerService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__FUNCTIONS_H_
#define TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "toms_msg/msg/rosidl_generator_c__visibility_control.h"

#include "toms_msg/srv/detail/crawler_service__struct.h"

/// Initialize srv/CrawlerService message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * toms_msg__srv__CrawlerService_Request
 * )) before or use
 * toms_msg__srv__CrawlerService_Request__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Request__init(toms_msg__srv__CrawlerService_Request * msg);

/// Finalize srv/CrawlerService message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Request__fini(toms_msg__srv__CrawlerService_Request * msg);

/// Create srv/CrawlerService message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * toms_msg__srv__CrawlerService_Request__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
toms_msg__srv__CrawlerService_Request *
toms_msg__srv__CrawlerService_Request__create();

/// Destroy srv/CrawlerService message.
/**
 * It calls
 * toms_msg__srv__CrawlerService_Request__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Request__destroy(toms_msg__srv__CrawlerService_Request * msg);

/// Check for srv/CrawlerService message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Request__are_equal(const toms_msg__srv__CrawlerService_Request * lhs, const toms_msg__srv__CrawlerService_Request * rhs);

/// Copy a srv/CrawlerService message.
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
toms_msg__srv__CrawlerService_Request__copy(
  const toms_msg__srv__CrawlerService_Request * input,
  toms_msg__srv__CrawlerService_Request * output);

/// Initialize array of srv/CrawlerService messages.
/**
 * It allocates the memory for the number of elements and calls
 * toms_msg__srv__CrawlerService_Request__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Request__Sequence__init(toms_msg__srv__CrawlerService_Request__Sequence * array, size_t size);

/// Finalize array of srv/CrawlerService messages.
/**
 * It calls
 * toms_msg__srv__CrawlerService_Request__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Request__Sequence__fini(toms_msg__srv__CrawlerService_Request__Sequence * array);

/// Create array of srv/CrawlerService messages.
/**
 * It allocates the memory for the array and calls
 * toms_msg__srv__CrawlerService_Request__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
toms_msg__srv__CrawlerService_Request__Sequence *
toms_msg__srv__CrawlerService_Request__Sequence__create(size_t size);

/// Destroy array of srv/CrawlerService messages.
/**
 * It calls
 * toms_msg__srv__CrawlerService_Request__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Request__Sequence__destroy(toms_msg__srv__CrawlerService_Request__Sequence * array);

/// Check for srv/CrawlerService message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Request__Sequence__are_equal(const toms_msg__srv__CrawlerService_Request__Sequence * lhs, const toms_msg__srv__CrawlerService_Request__Sequence * rhs);

/// Copy an array of srv/CrawlerService messages.
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
toms_msg__srv__CrawlerService_Request__Sequence__copy(
  const toms_msg__srv__CrawlerService_Request__Sequence * input,
  toms_msg__srv__CrawlerService_Request__Sequence * output);

/// Initialize srv/CrawlerService message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * toms_msg__srv__CrawlerService_Response
 * )) before or use
 * toms_msg__srv__CrawlerService_Response__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Response__init(toms_msg__srv__CrawlerService_Response * msg);

/// Finalize srv/CrawlerService message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Response__fini(toms_msg__srv__CrawlerService_Response * msg);

/// Create srv/CrawlerService message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * toms_msg__srv__CrawlerService_Response__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
toms_msg__srv__CrawlerService_Response *
toms_msg__srv__CrawlerService_Response__create();

/// Destroy srv/CrawlerService message.
/**
 * It calls
 * toms_msg__srv__CrawlerService_Response__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Response__destroy(toms_msg__srv__CrawlerService_Response * msg);

/// Check for srv/CrawlerService message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Response__are_equal(const toms_msg__srv__CrawlerService_Response * lhs, const toms_msg__srv__CrawlerService_Response * rhs);

/// Copy a srv/CrawlerService message.
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
toms_msg__srv__CrawlerService_Response__copy(
  const toms_msg__srv__CrawlerService_Response * input,
  toms_msg__srv__CrawlerService_Response * output);

/// Initialize array of srv/CrawlerService messages.
/**
 * It allocates the memory for the number of elements and calls
 * toms_msg__srv__CrawlerService_Response__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Response__Sequence__init(toms_msg__srv__CrawlerService_Response__Sequence * array, size_t size);

/// Finalize array of srv/CrawlerService messages.
/**
 * It calls
 * toms_msg__srv__CrawlerService_Response__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Response__Sequence__fini(toms_msg__srv__CrawlerService_Response__Sequence * array);

/// Create array of srv/CrawlerService messages.
/**
 * It allocates the memory for the array and calls
 * toms_msg__srv__CrawlerService_Response__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
toms_msg__srv__CrawlerService_Response__Sequence *
toms_msg__srv__CrawlerService_Response__Sequence__create(size_t size);

/// Destroy array of srv/CrawlerService messages.
/**
 * It calls
 * toms_msg__srv__CrawlerService_Response__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
void
toms_msg__srv__CrawlerService_Response__Sequence__destroy(toms_msg__srv__CrawlerService_Response__Sequence * array);

/// Check for srv/CrawlerService message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_toms_msg
bool
toms_msg__srv__CrawlerService_Response__Sequence__are_equal(const toms_msg__srv__CrawlerService_Response__Sequence * lhs, const toms_msg__srv__CrawlerService_Response__Sequence * rhs);

/// Copy an array of srv/CrawlerService messages.
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
toms_msg__srv__CrawlerService_Response__Sequence__copy(
  const toms_msg__srv__CrawlerService_Response__Sequence * input,
  toms_msg__srv__CrawlerService_Response__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__FUNCTIONS_H_
