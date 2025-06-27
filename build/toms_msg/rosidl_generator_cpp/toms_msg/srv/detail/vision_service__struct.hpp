// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:srv/VisionService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__VISION_SERVICE__STRUCT_HPP_
#define TOMS_MSG__SRV__DETAIL__VISION_SERVICE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__VisionService_Request __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__VisionService_Request __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct VisionService_Request_
{
  using Type = VisionService_Request_<ContainerAllocator>;

  explicit VisionService_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->task = "";
      this->direction = "";
    }
  }

  explicit VisionService_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : task(_alloc),
    direction(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->task = "";
      this->direction = "";
    }
  }

  // field types and members
  using _task_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _task_type task;
  using _direction_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _direction_type direction;

  // setters for named parameter idiom
  Type & set__task(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->task = _arg;
    return *this;
  }
  Type & set__direction(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->direction = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::VisionService_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::VisionService_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::VisionService_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::VisionService_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__VisionService_Request
    std::shared_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__VisionService_Request
    std::shared_ptr<toms_msg::srv::VisionService_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const VisionService_Request_ & other) const
  {
    if (this->task != other.task) {
      return false;
    }
    if (this->direction != other.direction) {
      return false;
    }
    return true;
  }
  bool operator!=(const VisionService_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct VisionService_Request_

// alias to use template instance with default allocator
using VisionService_Request =
  toms_msg::srv::VisionService_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg


// Include directives for member types
// Member 'target_pos'
#include "toms_msg/msg/detail/tomato_pos__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__VisionService_Response __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__VisionService_Response __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct VisionService_Response_
{
  using Type = VisionService_Response_<ContainerAllocator>;

  explicit VisionService_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : target_pos(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->detect_check = false;
    }
  }

  explicit VisionService_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : target_pos(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->detect_check = false;
    }
  }

  // field types and members
  using _detect_check_type =
    bool;
  _detect_check_type detect_check;
  using _target_pos_type =
    toms_msg::msg::TomatoPos_<ContainerAllocator>;
  _target_pos_type target_pos;

  // setters for named parameter idiom
  Type & set__detect_check(
    const bool & _arg)
  {
    this->detect_check = _arg;
    return *this;
  }
  Type & set__target_pos(
    const toms_msg::msg::TomatoPos_<ContainerAllocator> & _arg)
  {
    this->target_pos = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::VisionService_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::VisionService_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::VisionService_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::VisionService_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__VisionService_Response
    std::shared_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__VisionService_Response
    std::shared_ptr<toms_msg::srv::VisionService_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const VisionService_Response_ & other) const
  {
    if (this->detect_check != other.detect_check) {
      return false;
    }
    if (this->target_pos != other.target_pos) {
      return false;
    }
    return true;
  }
  bool operator!=(const VisionService_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct VisionService_Response_

// alias to use template instance with default allocator
using VisionService_Response =
  toms_msg::srv::VisionService_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg

namespace toms_msg
{

namespace srv
{

struct VisionService
{
  using Request = toms_msg::srv::VisionService_Request;
  using Response = toms_msg::srv::VisionService_Response;
};

}  // namespace srv

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__VISION_SERVICE__STRUCT_HPP_
