// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from smach_msgs:msg/SmachContainerInitialStatusCmd.idl
// generated code does not contain a copyright notice
#include "smach_msgs/msg/detail/smach_container_initial_status_cmd__rosidl_typesupport_fastrtps_cpp.hpp"
#include "smach_msgs/msg/detail/smach_container_initial_status_cmd__struct.hpp"

#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

namespace smach_msgs
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_smach_msgs
cdr_serialize(
  const smach_msgs::msg::SmachContainerInitialStatusCmd & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: path
  cdr << ros_message.path;
  // Member: initial_states
  {
    cdr << ros_message.initial_states;
  }
  // Member: local_data
  {
    cdr << ros_message.local_data;
  }
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_smach_msgs
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  smach_msgs::msg::SmachContainerInitialStatusCmd & ros_message)
{
  // Member: path
  cdr >> ros_message.path;

  // Member: initial_states
  {
    cdr >> ros_message.initial_states;
  }

  // Member: local_data
  {
    cdr >> ros_message.local_data;
  }

  return true;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_smach_msgs
get_serialized_size(
  const smach_msgs::msg::SmachContainerInitialStatusCmd & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: path
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message.path.size() + 1);
  // Member: initial_states
  {
    size_t array_size = ros_message.initial_states.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        (ros_message.initial_states[index].size() + 1);
    }
  }
  // Member: local_data
  {
    size_t array_size = ros_message.local_data.size();

    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);
    size_t item_size = sizeof(ros_message.local_data[0]);
    current_alignment += array_size * item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_smach_msgs
max_serialized_size_SmachContainerInitialStatusCmd(
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


  // Member: path
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

  // Member: initial_states
  {
    size_t array_size = 0;
    full_bounded = false;
    is_plain = false;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    full_bounded = false;
    is_plain = false;
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        1;
    }
  }

  // Member: local_data
  {
    size_t array_size = 0;
    full_bounded = false;
    is_plain = false;
    current_alignment += padding +
      eprosima::fastcdr::Cdr::alignment(current_alignment, padding);

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = smach_msgs::msg::SmachContainerInitialStatusCmd;
    is_plain =
      (
      offsetof(DataType, local_data) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _SmachContainerInitialStatusCmd__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const smach_msgs::msg::SmachContainerInitialStatusCmd *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _SmachContainerInitialStatusCmd__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<smach_msgs::msg::SmachContainerInitialStatusCmd *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _SmachContainerInitialStatusCmd__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const smach_msgs::msg::SmachContainerInitialStatusCmd *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _SmachContainerInitialStatusCmd__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_SmachContainerInitialStatusCmd(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _SmachContainerInitialStatusCmd__callbacks = {
  "smach_msgs::msg",
  "SmachContainerInitialStatusCmd",
  _SmachContainerInitialStatusCmd__cdr_serialize,
  _SmachContainerInitialStatusCmd__cdr_deserialize,
  _SmachContainerInitialStatusCmd__get_serialized_size,
  _SmachContainerInitialStatusCmd__max_serialized_size
};

static rosidl_message_type_support_t _SmachContainerInitialStatusCmd__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_SmachContainerInitialStatusCmd__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace smach_msgs

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_smach_msgs
const rosidl_message_type_support_t *
get_message_type_support_handle<smach_msgs::msg::SmachContainerInitialStatusCmd>()
{
  return &smach_msgs::msg::typesupport_fastrtps_cpp::_SmachContainerInitialStatusCmd__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, smach_msgs, msg, SmachContainerInitialStatusCmd)() {
  return &smach_msgs::msg::typesupport_fastrtps_cpp::_SmachContainerInitialStatusCmd__handle;
}

#ifdef __cplusplus
}
#endif
