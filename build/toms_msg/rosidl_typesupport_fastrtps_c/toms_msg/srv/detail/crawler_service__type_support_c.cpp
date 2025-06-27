// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from toms_msg:srv/CrawlerService.idl
// generated code does not contain a copyright notice
#include "toms_msg/srv/detail/crawler_service__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "toms_msg/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "toms_msg/srv/detail/crawler_service__struct.h"
#include "toms_msg/srv/detail/crawler_service__functions.h"
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

#include "rosidl_runtime_c/string.h"  // req_dir
#include "rosidl_runtime_c/string_functions.h"  // req_dir

// forward declare type support functions


using _CrawlerService_Request__ros_msg_type = toms_msg__srv__CrawlerService_Request;

static bool _CrawlerService_Request__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _CrawlerService_Request__ros_msg_type * ros_message = static_cast<const _CrawlerService_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: req_dir
  {
    const rosidl_runtime_c__String * str = &ros_message->req_dir;
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

static bool _CrawlerService_Request__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _CrawlerService_Request__ros_msg_type * ros_message = static_cast<_CrawlerService_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: req_dir
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->req_dir.data) {
      rosidl_runtime_c__String__init(&ros_message->req_dir);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->req_dir,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'req_dir'\n");
      return false;
    }
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t get_serialized_size_toms_msg__srv__CrawlerService_Request(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _CrawlerService_Request__ros_msg_type * ros_message = static_cast<const _CrawlerService_Request__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name req_dir
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->req_dir.size + 1);

  return current_alignment - initial_alignment;
}

static uint32_t _CrawlerService_Request__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_toms_msg__srv__CrawlerService_Request(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t max_serialized_size_toms_msg__srv__CrawlerService_Request(
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

  // member: req_dir
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
    using DataType = toms_msg__srv__CrawlerService_Request;
    is_plain =
      (
      offsetof(DataType, req_dir) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _CrawlerService_Request__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_toms_msg__srv__CrawlerService_Request(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_CrawlerService_Request = {
  "toms_msg::srv",
  "CrawlerService_Request",
  _CrawlerService_Request__cdr_serialize,
  _CrawlerService_Request__cdr_deserialize,
  _CrawlerService_Request__get_serialized_size,
  _CrawlerService_Request__max_serialized_size
};

static rosidl_message_type_support_t _CrawlerService_Request__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_CrawlerService_Request,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, CrawlerService_Request)() {
  return &_CrawlerService_Request__type_support;
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
// #include "toms_msg/srv/detail/crawler_service__struct.h"
// already included above
// #include "toms_msg/srv/detail/crawler_service__functions.h"
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

// already included above
// #include "rosidl_runtime_c/string.h"  // res_dir
// already included above
// #include "rosidl_runtime_c/string_functions.h"  // res_dir
#include "std_msgs/msg/detail/int32__functions.h"  // pulse

// forward declare type support functions
ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_toms_msg
size_t get_serialized_size_std_msgs__msg__Int32(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_toms_msg
size_t max_serialized_size_std_msgs__msg__Int32(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_toms_msg
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, std_msgs, msg, Int32)();


using _CrawlerService_Response__ros_msg_type = toms_msg__srv__CrawlerService_Response;

static bool _CrawlerService_Response__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _CrawlerService_Response__ros_msg_type * ros_message = static_cast<const _CrawlerService_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: res_dir
  {
    const rosidl_runtime_c__String * str = &ros_message->res_dir;
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

  // Field name: pulse
  {
    const message_type_support_callbacks_t * callbacks =
      static_cast<const message_type_support_callbacks_t *>(
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(
        rosidl_typesupport_fastrtps_c, std_msgs, msg, Int32
      )()->data);
    if (!callbacks->cdr_serialize(
        &ros_message->pulse, cdr))
    {
      return false;
    }
  }

  return true;
}

static bool _CrawlerService_Response__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _CrawlerService_Response__ros_msg_type * ros_message = static_cast<_CrawlerService_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: res_dir
  {
    std::string tmp;
    cdr >> tmp;
    if (!ros_message->res_dir.data) {
      rosidl_runtime_c__String__init(&ros_message->res_dir);
    }
    bool succeeded = rosidl_runtime_c__String__assign(
      &ros_message->res_dir,
      tmp.c_str());
    if (!succeeded) {
      fprintf(stderr, "failed to assign string into field 'res_dir'\n");
      return false;
    }
  }

  // Field name: pulse
  {
    const message_type_support_callbacks_t * callbacks =
      static_cast<const message_type_support_callbacks_t *>(
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(
        rosidl_typesupport_fastrtps_c, std_msgs, msg, Int32
      )()->data);
    if (!callbacks->cdr_deserialize(
        cdr, &ros_message->pulse))
    {
      return false;
    }
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t get_serialized_size_toms_msg__srv__CrawlerService_Response(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _CrawlerService_Response__ros_msg_type * ros_message = static_cast<const _CrawlerService_Response__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name res_dir
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message->res_dir.size + 1);
  // field.name pulse

  current_alignment += get_serialized_size_std_msgs__msg__Int32(
    &(ros_message->pulse), current_alignment);

  return current_alignment - initial_alignment;
}

static uint32_t _CrawlerService_Response__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_toms_msg__srv__CrawlerService_Response(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_toms_msg
size_t max_serialized_size_toms_msg__srv__CrawlerService_Response(
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

  // member: res_dir
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
  // member: pulse
  {
    size_t array_size = 1;


    last_member_size = 0;
    for (size_t index = 0; index < array_size; ++index) {
      bool inner_full_bounded;
      bool inner_is_plain;
      size_t inner_size;
      inner_size =
        max_serialized_size_std_msgs__msg__Int32(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = toms_msg__srv__CrawlerService_Response;
    is_plain =
      (
      offsetof(DataType, pulse) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _CrawlerService_Response__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_toms_msg__srv__CrawlerService_Response(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_CrawlerService_Response = {
  "toms_msg::srv",
  "CrawlerService_Response",
  _CrawlerService_Response__cdr_serialize,
  _CrawlerService_Response__cdr_deserialize,
  _CrawlerService_Response__get_serialized_size,
  _CrawlerService_Response__max_serialized_size
};

static rosidl_message_type_support_t _CrawlerService_Response__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_CrawlerService_Response,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, CrawlerService_Response)() {
  return &_CrawlerService_Response__type_support;
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
#include "toms_msg/srv/crawler_service.h"

#if defined(__cplusplus)
extern "C"
{
#endif

static service_type_support_callbacks_t CrawlerService__callbacks = {
  "toms_msg::srv",
  "CrawlerService",
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, CrawlerService_Request)(),
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, CrawlerService_Response)(),
};

static rosidl_service_type_support_t CrawlerService__handle = {
  rosidl_typesupport_fastrtps_c__identifier,
  &CrawlerService__callbacks,
  get_service_typesupport_handle_function,
};

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, toms_msg, srv, CrawlerService)() {
  return &CrawlerService__handle;
}

#if defined(__cplusplus)
}
#endif
