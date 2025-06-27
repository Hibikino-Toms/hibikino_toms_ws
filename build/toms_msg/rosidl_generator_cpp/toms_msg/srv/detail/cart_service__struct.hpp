// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:srv/CartService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CART_SERVICE__STRUCT_HPP_
#define TOMS_MSG__SRV__DETAIL__CART_SERVICE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__CartService_Request __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__CartService_Request __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct CartService_Request_
{
  using Type = CartService_Request_<ContainerAllocator>;

  explicit CartService_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->move_value = 0;
      this->pwm_value = 0;
    }
  }

  explicit CartService_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->move_value = 0;
      this->pwm_value = 0;
    }
  }

  // field types and members
  using _move_value_type =
    int16_t;
  _move_value_type move_value;
  using _pwm_value_type =
    int16_t;
  _pwm_value_type pwm_value;

  // setters for named parameter idiom
  Type & set__move_value(
    const int16_t & _arg)
  {
    this->move_value = _arg;
    return *this;
  }
  Type & set__pwm_value(
    const int16_t & _arg)
  {
    this->pwm_value = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::CartService_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::CartService_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CartService_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CartService_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__CartService_Request
    std::shared_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__CartService_Request
    std::shared_ptr<toms_msg::srv::CartService_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CartService_Request_ & other) const
  {
    if (this->move_value != other.move_value) {
      return false;
    }
    if (this->pwm_value != other.pwm_value) {
      return false;
    }
    return true;
  }
  bool operator!=(const CartService_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CartService_Request_

// alias to use template instance with default allocator
using CartService_Request =
  toms_msg::srv::CartService_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__CartService_Response __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__CartService_Response __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct CartService_Response_
{
  using Type = CartService_Response_<ContainerAllocator>;

  explicit CartService_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->move_result = 0.0f;
    }
  }

  explicit CartService_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->move_result = 0.0f;
    }
  }

  // field types and members
  using _move_result_type =
    float;
  _move_result_type move_result;

  // setters for named parameter idiom
  Type & set__move_result(
    const float & _arg)
  {
    this->move_result = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::CartService_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::CartService_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CartService_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CartService_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__CartService_Response
    std::shared_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__CartService_Response
    std::shared_ptr<toms_msg::srv::CartService_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CartService_Response_ & other) const
  {
    if (this->move_result != other.move_result) {
      return false;
    }
    return true;
  }
  bool operator!=(const CartService_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CartService_Response_

// alias to use template instance with default allocator
using CartService_Response =
  toms_msg::srv::CartService_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg

namespace toms_msg
{

namespace srv
{

struct CartService
{
  using Request = toms_msg::srv::CartService_Request;
  using Response = toms_msg::srv::CartService_Response;
};

}  // namespace srv

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__CART_SERVICE__STRUCT_HPP_
