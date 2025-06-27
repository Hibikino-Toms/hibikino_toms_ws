// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from toms_msg:srv/CrawlerService.idl
// generated code does not contain a copyright notice

#ifndef TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__BUILDER_HPP_
#define TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "toms_msg/srv/detail/crawler_service__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_CrawlerService_Request_req_dir
{
public:
  Init_CrawlerService_Request_req_dir()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::toms_msg::srv::CrawlerService_Request req_dir(::toms_msg::srv::CrawlerService_Request::_req_dir_type arg)
  {
    msg_.req_dir = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::CrawlerService_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::CrawlerService_Request>()
{
  return toms_msg::srv::builder::Init_CrawlerService_Request_req_dir();
}

}  // namespace toms_msg


namespace toms_msg
{

namespace srv
{

namespace builder
{

class Init_CrawlerService_Response_pulse
{
public:
  explicit Init_CrawlerService_Response_pulse(::toms_msg::srv::CrawlerService_Response & msg)
  : msg_(msg)
  {}
  ::toms_msg::srv::CrawlerService_Response pulse(::toms_msg::srv::CrawlerService_Response::_pulse_type arg)
  {
    msg_.pulse = std::move(arg);
    return std::move(msg_);
  }

private:
  ::toms_msg::srv::CrawlerService_Response msg_;
};

class Init_CrawlerService_Response_res_dir
{
public:
  Init_CrawlerService_Response_res_dir()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_CrawlerService_Response_pulse res_dir(::toms_msg::srv::CrawlerService_Response::_res_dir_type arg)
  {
    msg_.res_dir = std::move(arg);
    return Init_CrawlerService_Response_pulse(msg_);
  }

private:
  ::toms_msg::srv::CrawlerService_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::toms_msg::srv::CrawlerService_Response>()
{
  return toms_msg::srv::builder::Init_CrawlerService_Response_res_dir();
}

}  // namespace toms_msg

#endif  // TOMS_MSG__SRV__DETAIL__CRAWLER_SERVICE__BUILDER_HPP_
