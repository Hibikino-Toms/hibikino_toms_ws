// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from toms_msg:srv/CrawlerService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__STRUCT_HPP_
#define TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__CrawlerService_Request __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__CrawlerService_Request __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct CrawlerService_Request_
{
  using Type = CrawlerService_Request_<ContainerAllocator>;

  explicit CrawlerService_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->req_dir = "";
    }
  }

  explicit CrawlerService_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : req_dir(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->req_dir = "";
    }
  }

  // field types and members
  using _req_dir_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _req_dir_type req_dir;

  // setters for named parameter idiom
  Type & set__req_dir(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->req_dir = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::CrawlerService_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::CrawlerService_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CrawlerService_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CrawlerService_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__CrawlerService_Request
    std::shared_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__CrawlerService_Request
    std::shared_ptr<toms_msg::srv::CrawlerService_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CrawlerService_Request_ & other) const
  {
    if (this->req_dir != other.req_dir) {
      return false;
    }
    return true;
  }
  bool operator!=(const CrawlerService_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CrawlerService_Request_

// alias to use template instance with default allocator
using CrawlerService_Request =
  toms_msg::srv::CrawlerService_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg


// Include directives for member types
// Member 'pulse'
#include "std_msgs/msg/detail/int32__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__toms_msg__srv__CrawlerService_Response __attribute__((deprecated))
#else
# define DEPRECATED__toms_msg__srv__CrawlerService_Response __declspec(deprecated)
#endif

namespace toms_msg
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct CrawlerService_Response_
{
  using Type = CrawlerService_Response_<ContainerAllocator>;

  explicit CrawlerService_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : pulse(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->res_dir = "";
    }
  }

  explicit CrawlerService_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : res_dir(_alloc),
    pulse(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->res_dir = "";
    }
  }

  // field types and members
  using _res_dir_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _res_dir_type res_dir;
  using _pulse_type =
    std_msgs::msg::Int32_<ContainerAllocator>;
  _pulse_type pulse;

  // setters for named parameter idiom
  Type & set__res_dir(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->res_dir = _arg;
    return *this;
  }
  Type & set__pulse(
    const std_msgs::msg::Int32_<ContainerAllocator> & _arg)
  {
    this->pulse = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    toms_msg::srv::CrawlerService_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const toms_msg::srv::CrawlerService_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CrawlerService_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      toms_msg::srv::CrawlerService_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__toms_msg__srv__CrawlerService_Response
    std::shared_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__toms_msg__srv__CrawlerService_Response
    std::shared_ptr<toms_msg::srv::CrawlerService_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CrawlerService_Response_ & other) const
  {
    if (this->res_dir != other.res_dir) {
      return false;
    }
    if (this->pulse != other.pulse) {
      return false;
    }
    return true;
  }
  bool operator!=(const CrawlerService_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CrawlerService_Response_

// alias to use template instance with default allocator
using CrawlerService_Response =
  toms_msg::srv::CrawlerService_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace toms_msg

namespace toms_msg
{

namespace srv
{

struct CrawlerService
{
  using Request = toms_msg::srv::CrawlerService_Request;
  using Response = toms_msg::srv::CrawlerService_Response;
};

}  // namespace srv

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__STRUCT_HPP_
