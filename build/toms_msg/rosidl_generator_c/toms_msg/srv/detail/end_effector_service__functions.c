// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from toms_msg:srv/EndEffectorService.idl
// generated code does not contain a copyright notice
#include "toms_msg/srv/detail/end_effector_service__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

// Include directives for member types
// Member `task`
#include "rosidl_runtime_c/string_functions.h"

bool
toms_msg__srv__EndEffectorService_Request__init(toms_msg__srv__EndEffectorService_Request * msg)
{
  if (!msg) {
    return false;
  }
  // task
  if (!rosidl_runtime_c__String__init(&msg->task)) {
    toms_msg__srv__EndEffectorService_Request__fini(msg);
    return false;
  }
  return true;
}

void
toms_msg__srv__EndEffectorService_Request__fini(toms_msg__srv__EndEffectorService_Request * msg)
{
  if (!msg) {
    return;
  }
  // task
  rosidl_runtime_c__String__fini(&msg->task);
}

bool
toms_msg__srv__EndEffectorService_Request__are_equal(const toms_msg__srv__EndEffectorService_Request * lhs, const toms_msg__srv__EndEffectorService_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // task
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->task), &(rhs->task)))
  {
    return false;
  }
  return true;
}

bool
toms_msg__srv__EndEffectorService_Request__copy(
  const toms_msg__srv__EndEffectorService_Request * input,
  toms_msg__srv__EndEffectorService_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // task
  if (!rosidl_runtime_c__String__copy(
      &(input->task), &(output->task)))
  {
    return false;
  }
  return true;
}

toms_msg__srv__EndEffectorService_Request *
toms_msg__srv__EndEffectorService_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__srv__EndEffectorService_Request * msg = (toms_msg__srv__EndEffectorService_Request *)allocator.allocate(sizeof(toms_msg__srv__EndEffectorService_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(toms_msg__srv__EndEffectorService_Request));
  bool success = toms_msg__srv__EndEffectorService_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
toms_msg__srv__EndEffectorService_Request__destroy(toms_msg__srv__EndEffectorService_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    toms_msg__srv__EndEffectorService_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
toms_msg__srv__EndEffectorService_Request__Sequence__init(toms_msg__srv__EndEffectorService_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__srv__EndEffectorService_Request * data = NULL;

  if (size) {
    data = (toms_msg__srv__EndEffectorService_Request *)allocator.zero_allocate(size, sizeof(toms_msg__srv__EndEffectorService_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = toms_msg__srv__EndEffectorService_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        toms_msg__srv__EndEffectorService_Request__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
toms_msg__srv__EndEffectorService_Request__Sequence__fini(toms_msg__srv__EndEffectorService_Request__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      toms_msg__srv__EndEffectorService_Request__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

toms_msg__srv__EndEffectorService_Request__Sequence *
toms_msg__srv__EndEffectorService_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__srv__EndEffectorService_Request__Sequence * array = (toms_msg__srv__EndEffectorService_Request__Sequence *)allocator.allocate(sizeof(toms_msg__srv__EndEffectorService_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = toms_msg__srv__EndEffectorService_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
toms_msg__srv__EndEffectorService_Request__Sequence__destroy(toms_msg__srv__EndEffectorService_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    toms_msg__srv__EndEffectorService_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
toms_msg__srv__EndEffectorService_Request__Sequence__are_equal(const toms_msg__srv__EndEffectorService_Request__Sequence * lhs, const toms_msg__srv__EndEffectorService_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!toms_msg__srv__EndEffectorService_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
toms_msg__srv__EndEffectorService_Request__Sequence__copy(
  const toms_msg__srv__EndEffectorService_Request__Sequence * input,
  toms_msg__srv__EndEffectorService_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(toms_msg__srv__EndEffectorService_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    toms_msg__srv__EndEffectorService_Request * data =
      (toms_msg__srv__EndEffectorService_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!toms_msg__srv__EndEffectorService_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          toms_msg__srv__EndEffectorService_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!toms_msg__srv__EndEffectorService_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


bool
toms_msg__srv__EndEffectorService_Response__init(toms_msg__srv__EndEffectorService_Response * msg)
{
  if (!msg) {
    return false;
  }
  // task_done
  return true;
}

void
toms_msg__srv__EndEffectorService_Response__fini(toms_msg__srv__EndEffectorService_Response * msg)
{
  if (!msg) {
    return;
  }
  // task_done
}

bool
toms_msg__srv__EndEffectorService_Response__are_equal(const toms_msg__srv__EndEffectorService_Response * lhs, const toms_msg__srv__EndEffectorService_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // task_done
  if (lhs->task_done != rhs->task_done) {
    return false;
  }
  return true;
}

bool
toms_msg__srv__EndEffectorService_Response__copy(
  const toms_msg__srv__EndEffectorService_Response * input,
  toms_msg__srv__EndEffectorService_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // task_done
  output->task_done = input->task_done;
  return true;
}

toms_msg__srv__EndEffectorService_Response *
toms_msg__srv__EndEffectorService_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__srv__EndEffectorService_Response * msg = (toms_msg__srv__EndEffectorService_Response *)allocator.allocate(sizeof(toms_msg__srv__EndEffectorService_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(toms_msg__srv__EndEffectorService_Response));
  bool success = toms_msg__srv__EndEffectorService_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
toms_msg__srv__EndEffectorService_Response__destroy(toms_msg__srv__EndEffectorService_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    toms_msg__srv__EndEffectorService_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
toms_msg__srv__EndEffectorService_Response__Sequence__init(toms_msg__srv__EndEffectorService_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__srv__EndEffectorService_Response * data = NULL;

  if (size) {
    data = (toms_msg__srv__EndEffectorService_Response *)allocator.zero_allocate(size, sizeof(toms_msg__srv__EndEffectorService_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = toms_msg__srv__EndEffectorService_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        toms_msg__srv__EndEffectorService_Response__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
toms_msg__srv__EndEffectorService_Response__Sequence__fini(toms_msg__srv__EndEffectorService_Response__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      toms_msg__srv__EndEffectorService_Response__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

toms_msg__srv__EndEffectorService_Response__Sequence *
toms_msg__srv__EndEffectorService_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__srv__EndEffectorService_Response__Sequence * array = (toms_msg__srv__EndEffectorService_Response__Sequence *)allocator.allocate(sizeof(toms_msg__srv__EndEffectorService_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = toms_msg__srv__EndEffectorService_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
toms_msg__srv__EndEffectorService_Response__Sequence__destroy(toms_msg__srv__EndEffectorService_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    toms_msg__srv__EndEffectorService_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
toms_msg__srv__EndEffectorService_Response__Sequence__are_equal(const toms_msg__srv__EndEffectorService_Response__Sequence * lhs, const toms_msg__srv__EndEffectorService_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!toms_msg__srv__EndEffectorService_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
toms_msg__srv__EndEffectorService_Response__Sequence__copy(
  const toms_msg__srv__EndEffectorService_Response__Sequence * input,
  toms_msg__srv__EndEffectorService_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(toms_msg__srv__EndEffectorService_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    toms_msg__srv__EndEffectorService_Response * data =
      (toms_msg__srv__EndEffectorService_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!toms_msg__srv__EndEffectorService_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          toms_msg__srv__EndEffectorService_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!toms_msg__srv__EndEffectorService_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
