// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from toms_msg:srv/CartService.idl
// generated code does not contain a copyright notice
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>
#include <stdbool.h>
#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-function"
#endif
#include "numpy/ndarrayobject.h"
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif
#include "rosidl_runtime_c/visibility_control.h"
#include "toms_msg/srv/detail/cart_service__struct.h"
#include "toms_msg/srv/detail/cart_service__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool toms_msg__srv__cart_service__request__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[47];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("toms_msg.srv._cart_service.CartService_Request", full_classname_dest, 46) == 0);
  }
  toms_msg__srv__CartService_Request * ros_message = _ros_message;
  {  // move_value
    PyObject * field = PyObject_GetAttrString(_pymsg, "move_value");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->move_value = (int16_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }
  {  // pwm_value
    PyObject * field = PyObject_GetAttrString(_pymsg, "pwm_value");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->pwm_value = (int16_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * toms_msg__srv__cart_service__request__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of CartService_Request */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("toms_msg.srv._cart_service");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "CartService_Request");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  toms_msg__srv__CartService_Request * ros_message = (toms_msg__srv__CartService_Request *)raw_ros_message;
  {  // move_value
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->move_value);
    {
      int rc = PyObject_SetAttrString(_pymessage, "move_value", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // pwm_value
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->pwm_value);
    {
      int rc = PyObject_SetAttrString(_pymessage, "pwm_value", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
// already included above
// #include <Python.h>
// already included above
// #include <stdbool.h>
// already included above
// #include "numpy/ndarrayobject.h"
// already included above
// #include "rosidl_runtime_c/visibility_control.h"
// already included above
// #include "toms_msg/srv/detail/cart_service__struct.h"
// already included above
// #include "toms_msg/srv/detail/cart_service__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool toms_msg__srv__cart_service__response__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[48];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("toms_msg.srv._cart_service.CartService_Response", full_classname_dest, 47) == 0);
  }
  toms_msg__srv__CartService_Response * ros_message = _ros_message;
  {  // move_result
    PyObject * field = PyObject_GetAttrString(_pymsg, "move_result");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->move_result = (float)PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * toms_msg__srv__cart_service__response__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of CartService_Response */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("toms_msg.srv._cart_service");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "CartService_Response");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  toms_msg__srv__CartService_Response * ros_message = (toms_msg__srv__CartService_Response *)raw_ros_message;
  {  // move_result
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->move_result);
    {
      int rc = PyObject_SetAttrString(_pymessage, "move_result", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
