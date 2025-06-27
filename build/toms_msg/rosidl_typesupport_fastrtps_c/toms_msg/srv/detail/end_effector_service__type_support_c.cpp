// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from toms_msg:srv/EndEffectorService.idl
// generated code does not contain a copyright notice
#include "toms_msg/srv/detail/end_effector_service__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "toms_msg/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "toms_msg/srv/detail/end_effector_service__struct.h"
#include "toms_msg/srv/detail/end_effector_service__functions.h"
#include "fastcdr/Cdr.h"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif

#include "rosidl_runtime_c/string.h"  // task
#include "rosidl_runtime_c/string_functions.h"  // task

// forward declare type support functions


using _EndEffectorService_Request__ros_msg_type = toms_msg__srv__EndEffectorService_Request;

static bool _EndEffectorService_Request__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _EndEffectorService_Request__ros_msg_type * ros_message = static_cast<const _EndEffectorService_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: task
  {
    const rosidl_runtime_c__String * str = &ros_message->task;
    if (str->capacity == 0 || str->capacity <= str->size) {
      fprintf(stderr, "string capacity not greater than size\n");
      return false;
    }
    if (str->data[str->size] != '\0') {
      fprintf(stderr, "string not null-terminated\n");
      return false;
    }
    cdr << str->data;
  }

  return true;
}

static bool _EndEffectorService_Request__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _EndEffectorService_Request__ros_msg_type * ros_message = static_cast<_EndEffectorService_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: task
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->task.data) {
      rosidl_runtime_c__String__init(&ros_message->task);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->task,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'task'\n");
      return false;
    }
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t get_serialized_size_toms_msg__srv__EndEffectorService_Request(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _EndEffectorService_Request__ros_msg_type * ros_message = static_cast<const _EndEffectorService_Request__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name task
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->task.size + 1);

  return current_alignment - initial_alignment;
}

static uint32_t _EndEffectorService_Request__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_toms_msg__srv__EndEffectorService_Request(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t max_serialized_size_toms_msg__srv__EndEffectorService_Request(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;

  // member: task
  {
    size_t array_size = 1;

    full_bounded = false;
    is_plain = false;
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        1;
    }
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = toms_msg__srv__EndEffectorService_Request;
    is_plain =
      (
      offsetof(DataType, task) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _EndEffectorService_Request__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_toms_msg__srv__EndEffectorService_Request(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_EndEffectorService_Request = {
  "toms_msg::srv",
  "EndEffectorService_Request",
  _EndEffectorService_Request__cdr_serialize,
  _EndEffectorService_Request__cdr_deserialize,
  _EndEffectorService_Request__get_serialized_size,
  _EndEffectorService_Request__max_serialized_size
};

static rosidl_message_type_support_t _EndEffectorService_Request__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_EndEffectorService_Request,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, EndEffectorService_Request)() {
  return &_EndEffectorService_Request__type_support;
}

#if defined(__cplusplus)
}
#endif

// already included above
// #include <cassert>
// already included above
// #include <limits>
// already included above
// #include <string>
// already included above
// #include "rosidl_typesupport_fastrtps_c/identifier.h"
// already included above
// #include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
// already included above
// #include "toms_msg/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
// already included above
// #include "toms_msg/srv/detail/end_effector_service__struct.h"
// already included above
// #include "toms_msg/srv/detail/end_effector_service__functions.h"
// already included above
// #include "fastcdr/Cdr.h"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif


// forward declare type support functions


using _EndEffectorService_Response__ros_msg_type = toms_msg__srv__EndEffectorService_Response;

static bool _EndEffectorService_Response__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _EndEffectorService_Response__ros_msg_type * ros_message = static_cast<const _EndEffectorService_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: task_done
  {
    cdr << (ros_message->task_done ? true : false);
  }

  return true;
}

static bool _EndEffectorService_Response__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _EndEffectorService_Response__ros_msg_type * ros_message = static_cast<_EndEffectorService_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: task_done
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message->task_done = tmp ? true : false;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t get_serialized_size_toms_msg__srv__EndEffectorService_Response(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _EndEffectorService_Response__ros_msg_type * ros_message = static_cast<const _EndEffectorService_Response__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name task_done
  {
    size_t item_size = sizeof(ros_message->task_done);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _EndEffectorService_Response__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_toms_msg__srv__EndEffectorService_Response(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t max_serialized_size_toms_msg__srv__EndEffectorService_Response(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;

  // member: task_done
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = toms_msg__srv__EndEffectorService_Response;
    is_plain =
      (
      offsetof(DataType, task_done) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _EndEffectorService_Response__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_toms_msg__srv__EndEffectorService_Response(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_EndEffectorService_Response = {
  "toms_msg::srv",
  "EndEffectorService_Response",
  _EndEffectorService_Response__cdr_serialize,
  _EndEffectorService_Response__cdr_deserialize,
  _EndEffectorService_Response__get_serialized_size,
  _EndEffectorService_Response__max_serialized_size
};

static rosidl_message_type_support_t _EndEffectorService_Response__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_EndEffectorService_Response,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, EndEffectorService_Response)() {
  return &_EndEffectorService_Response__type_support;
}

#if defined(__cplusplus)
}
#endif

#include "rosidl_typesupport_fastrtps_cpp/service_type_support.h"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_c/identifier.h"
// already included above
// #include "toms_msg/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "toms_msg/srv/end_effector_service.h"

#if defined(__cplusplus)
extern "C"
{
#endif

static service_type_support_callbacks_t EndEffectorService__callbacks = {
  "toms_msg::srv",
  "EndEffectorService",
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, EndEffectorService_Request)(),
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, EndEffectorService_Response)(),
};

static rosidl_service_type_support_t EndEffectorService__handle = {
  rosidl_typesupport_fastrtps_c__identifier,
  &EndEffectorService__callbacks,
  get_service_typesupport_handle_function,
};

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, EndEffectorService)() {
  return &EndEffectorService__handle;
}

#if defined(__cplusplus)
}
#endif
