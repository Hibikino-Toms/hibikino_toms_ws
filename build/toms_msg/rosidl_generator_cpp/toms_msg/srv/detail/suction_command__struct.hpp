// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:srv/SuctionCommand.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__STRUCT_HPP_
#define TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__SuctionCommand_Request __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__SuctionCommand_Request __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SuctionCommand_Request_
{
  using Type = SuctionCommand_Request_<ContainerAllocator>;

  explicit SuctionCommand_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->command = "";
    }
  }

  explicit SuctionCommand_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : command(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->command = "";
    }
  }

  // field types and members
  using _command_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _command_type command;

  // setters for named parameter idiom
  Type & set__command(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->command = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::SuctionCommand_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::SuctionCommand_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::SuctionCommand_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::SuctionCommand_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__SuctionCommand_Request
    std::shared_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__SuctionCommand_Request
    std::shared_ptr<toms_msg::srv::SuctionCommand_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SuctionCommand_Request_ & other) const
  {
    if (this->command != other.command) {
      return false;
    }
    return true;
  }
  bool operator!=(const SuctionCommand_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SuctionCommand_Request_

// alias to use template instance with default allocator
using SuctionCommand_Request =
  toms_msg::srv::SuctionCommand_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__SuctionCommand_Response __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__SuctionCommand_Response __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SuctionCommand_Response_
{
  using Type = SuctionCommand_Response_<ContainerAllocator>;

  explicit SuctionCommand_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->answer = "";
    }
  }

  explicit SuctionCommand_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : answer(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->answer = "";
    }
  }

  // field types and members
  using _answer_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _answer_type answer;

  // setters for named parameter idiom
  Type & set__answer(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->answer = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::SuctionCommand_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::SuctionCommand_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::SuctionCommand_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::SuctionCommand_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__SuctionCommand_Response
    std::shared_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__SuctionCommand_Response
    std::shared_ptr<toms_msg::srv::SuctionCommand_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SuctionCommand_Response_ & other) const
  {
    if (this->answer != other.answer) {
      return false;
    }
    return true;
  }
  bool operator!=(const SuctionCommand_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SuctionCommand_Response_

// alias to use template instance with default allocator
using SuctionCommand_Response =
  toms_msg::srv::SuctionCommand_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg

namespace toms_msg
{

namespace srv
{

struct SuctionCommand
{
  using Request = toms_msg::srv::SuctionCommand_Request;
  using Response = toms_msg::srv::SuctionCommand_Response;
};

}  // namespace srv

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__SUCTION_COMMAND__STRUCT_HPP_
