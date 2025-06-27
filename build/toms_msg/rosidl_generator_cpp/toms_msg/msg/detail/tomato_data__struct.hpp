// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:msg/TomatoData.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__MSG__DETAIL__TOMATO_DATA__STRUCT_HPP_
#define TOMS_MSG__MSG__DETAIL__TOMATO_DATA__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__toms_msg__msg__TomatoData __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__msg__TomatoData __declspec(deprecated)
#endif

namespace toms_msg
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct TomatoData_
{
  using Type = TomatoData_<ContainerAllocator>;

  explicit TomatoData_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->x = 0;
      this->y = 0;
      this->z = 0;
      this->approach_direction = 0;
    }
  }

  explicit TomatoData_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->x = 0;
      this->y = 0;
      this->z = 0;
      this->approach_direction = 0;
    }
  }

  // field types and members
  using _x_type =
    int16_t;
  _x_type x;
  using _y_type =
    int16_t;
  _y_type y;
  using _z_type =
    int16_t;
  _z_type z;
  using _approach_direction_type =
    int16_t;
  _approach_direction_type approach_direction;

  // setters for named parameter idiom
  Type & set__x(
    const int16_t & _arg)
  {
    this->x = _arg;
    return *this;
  }
  Type & set__y(
    const int16_t & _arg)
  {
    this->y = _arg;
    return *this;
  }
  Type & set__z(
    const int16_t & _arg)
  {
    this->z = _arg;
    return *this;
  }
  Type & set__approach_direction(
    const int16_t & _arg)
  {
    this->approach_direction = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::msg::TomatoData_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::msg::TomatoData_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::msg::TomatoData_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::msg::TomatoData_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::msg::TomatoData_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::msg::TomatoData_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::msg::TomatoData_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::msg::TomatoData_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::msg::TomatoData_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::msg::TomatoData_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__msg__TomatoData
    std::shared_ptr<toms_msg::msg::TomatoData_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__msg__TomatoData
    std::shared_ptr<toms_msg::msg::TomatoData_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const TomatoData_ & other) const
  {
    if (this->x != other.x) {
      return false;
    }
    if (this->y != other.y) {
      return false;
    }
    if (this->z != other.z) {
      return false;
    }
    if (this->approach_direction != other.approach_direction) {
      return false;
    }
    return true;
  }
  bool operator!=(const TomatoData_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct TomatoData_

// alias to use template instance with default allocator
using TomatoData =
  toms_msg::msg::TomatoData_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace toms_msg

#endif  // TOMS_MSG__MSG__DETAIL__TOMATO_DATA__STRUCT_HPP_
