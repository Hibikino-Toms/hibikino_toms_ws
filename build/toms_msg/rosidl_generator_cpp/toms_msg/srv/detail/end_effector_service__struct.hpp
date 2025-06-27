// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:srv/EndEffectorService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__STRUCT_HPP_
#define TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__EndEffectorService_Request __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__EndEffectorService_Request __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct EndEffectorService_Request_
{
  using Type = EndEffectorService_Request_<ContainerAllocator>;

  explicit EndEffectorService_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->task = "";
    }
  }

  explicit EndEffectorService_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : task(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->task = "";
    }
  }

  // field types and members
  using _task_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _task_type task;

  // setters for named parameter idiom
  Type & set__task(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->task = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::EndEffectorService_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::EndEffectorService_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::EndEffectorService_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::EndEffectorService_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__EndEffectorService_Request
    std::shared_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__EndEffectorService_Request
    std::shared_ptr<toms_msg::srv::EndEffectorService_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const EndEffectorService_Request_ & other) const
  {
    if (this->task != other.task) {
      return false;
    }
    return true;
  }
  bool operator!=(const EndEffectorService_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct EndEffectorService_Request_

// alias to use template instance with default allocator
using EndEffectorService_Request =
  toms_msg::srv::EndEffectorService_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__EndEffectorService_Response __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__EndEffectorService_Response __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct EndEffectorService_Response_
{
  using Type = EndEffectorService_Response_<ContainerAllocator>;

  explicit EndEffectorService_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->task_done = false;
    }
  }

  explicit EndEffectorService_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->task_done = false;
    }
  }

  // field types and members
  using _task_done_type =
    bool;
  _task_done_type task_done;

  // setters for named parameter idiom
  Type & set__task_done(
    const bool & _arg)
  {
    this->task_done = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::EndEffectorService_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::EndEffectorService_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::EndEffectorService_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::EndEffectorService_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__EndEffectorService_Response
    std::shared_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__EndEffectorService_Response
    std::shared_ptr<toms_msg::srv::EndEffectorService_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const EndEffectorService_Response_ & other) const
  {
    if (this->task_done != other.task_done) {
      return false;
    }
    return true;
  }
  bool operator!=(const EndEffectorService_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct EndEffectorService_Response_

// alias to use template instance with default allocator
using EndEffectorService_Response =
  toms_msg::srv::EndEffectorService_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg

namespace toms_msg
{

namespace srv
{

struct EndEffectorService
{
  using Request = toms_msg::srv::EndEffectorService_Request;
  using Response = toms_msg::srv::EndEffectorService_Response;
};

}  // namespace srv

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__END_EFFECTOR_SERVICE__STRUCT_HPP_
