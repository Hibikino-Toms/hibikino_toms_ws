// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_POS__STRUCT_HPP_
#define TOMS_MSG__MSG__DETAIL__TOMATO_POS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'tomato_data'
#include "toms_msg/msg/detail/tomato_data__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__toms_msg__msg__TomatoPos __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__msg__TomatoPos __declspec(deprecated)
#endif

namespace toms_msg
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct TomatoPos_
{
  using Type = TomatoPos_<ContainerAllocator>;

  explicit TomatoPos_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_init;
  }

  explicit TomatoPos_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_init;
    (void)_alloc;
  }

  // field types and members
  using _tomato_data_type =
    std::vector<toms_msg::msg::TomatoData_<ContainerAllocator>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<toms_msg::msg::TomatoData_<ContainerAllocator>>>;
  _tomato_data_type tomato_data;

  // setters for named parameter idiom
  Type & set__tomato_data(
    const std::vector<toms_msg::msg::TomatoData_<ContainerAllocator>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<toms_msg::msg::TomatoData_<ContainerAllocator>>> & _arg)
  {
    this->tomato_data = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::msg::TomatoPos_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::msg::TomatoPos_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::msg::TomatoPos_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::msg::TomatoPos_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__msg__TomatoPos
    std::shared_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__msg__TomatoPos
    std::shared_ptr<toms_msg::msg::TomatoPos_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const TomatoPos_ & other) const
  {
    if (this->tomato_data != other.tomato_data) {
      return false;
    }
    return true;
  }
  bool operator!=(const TomatoPos_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct TomatoPos_

// alias to use template instance with default allocator
using TomatoPos =
  toms_msg::msg::TomatoPos_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace toms_msg

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_POS__STRUCT_HPP_
