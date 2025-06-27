// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from toms_msg:srv/CrawlerService.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "toms_msg/srv/detail/crawler_service__rosidl_typesupport_introspection_c.h"
#include "toms_msg/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "toms_msg/srv/detail/crawler_service__functions.h"
#include "toms_msg/srv/detail/crawler_service__struct.h"


// Include directives for member types
// Member `req_dir`
#include "rosidl_runtime_c/string_functions.h"

#ifdef __cplusplus
extern "C"
{
#endif

void toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  toms_msg__srv__CrawlerService_Request__init(message_memory);
}

void toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_fini_function(void * message_memory)
{
  toms_msg__srv__CrawlerService_Request__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_member_array[1] = {
  {
    "req_dir",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__srv__CrawlerService_Request, req_dir),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_members = {
  "toms_msg__srv",  // message namespace
  "CrawlerService_Request",  // message name
  1,  // number of fields
  sizeof(toms_msg__srv__CrawlerService_Request),
  toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_member_array,  // message members
  toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_type_support_handle = {
  0,
  &toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_toms_msg
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService_Request)() {
  if (!toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_type_support_handle.typesupport_identifier) {
    toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &toms_msg__srv__CrawlerService_Request__rosidl_typesupport_introspection_c__CrawlerService_Request_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

// already included above
// #include <stddef.h>
// already included above
// #include "toms_msg/srv/detail/crawler_service__rosidl_typesupport_introspection_c.h"
// already included above
// #include "toms_msg/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "rosidl_typesupport_introspection_c/field_types.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
// already included above
// #include "rosidl_typesupport_introspection_c/message_introspection.h"
// already included above
// #include "toms_msg/srv/detail/crawler_service__functions.h"
// already included above
// #include "toms_msg/srv/detail/crawler_service__struct.h"


// Include directives for member types
// Member `res_dir`
// already included above
// #include "rosidl_runtime_c/string_functions.h"
// Member `pulse`
#include "std_msgs/msg/int32.h"
// Member `pulse`
#include "std_msgs/msg/detail/int32__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  toms_msg__srv__CrawlerService_Response__init(message_memory);
}

void toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_fini_function(void * message_memory)
{
  toms_msg__srv__CrawlerService_Response__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_member_array[2] = {
  {
    "res_dir",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__srv__CrawlerService_Response, res_dir),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "pulse",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(toms_msg__srv__CrawlerService_Response, pulse),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_members = {
  "toms_msg__srv",  // message namespace
  "CrawlerService_Response",  // message name
  2,  // number of fields
  sizeof(toms_msg__srv__CrawlerService_Response),
  toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_member_array,  // message members
  toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_type_support_handle = {
  0,
  &toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_toms_msg
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService_Response)() {
  toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_member_array[1].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, std_msgs, msg, Int32)();
  if (!toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_type_support_handle.typesupport_identifier) {
    toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &toms_msg__srv__CrawlerService_Response__rosidl_typesupport_introspection_c__CrawlerService_Response_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "toms_msg/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "toms_msg/srv/detail/crawler_service__rosidl_typesupport_introspection_c.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/service_introspection.h"

// this is intentionally not const to allow initialization later to prevent an initialization race
static rosidl_typesupport_introspection_c__ServiceMembers toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_members = {
  "toms_msg__srv",  // service namespace
  "CrawlerService",  // service name
  // these two fields are initialized below on the first access
  NULL,  // request message
  // toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_Request_message_type_support_handle,
  NULL  // response message
  // toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_Response_message_type_support_handle
};

static rosidl_service_type_support_t toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_type_support_handle = {
  0,
  &toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_members,
  get_service_typesupport_handle_function,
};

// Forward declaration of request/response type support functions
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService_Request)();

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService_Response)();

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_toms_msg
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService)() {
  if (!toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_type_support_handle.typesupport_identifier) {
    toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  rosidl_typesupport_introspection_c__ServiceMembers * service_members =
    (rosidl_typesupport_introspection_c__ServiceMembers *)toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_type_support_handle.data;

  if (!service_members->request_members_) {
    service_members->request_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService_Request)()->data;
  }
  if (!service_members->response_members_) {
    service_members->response_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, toms_msg, srv, CrawlerService_Response)()->data;
  }

  return &toms_msg__srv__detail__crawler_service__rosidl_typesupport_introspection_c__CrawlerService_service_type_support_handle;
}
