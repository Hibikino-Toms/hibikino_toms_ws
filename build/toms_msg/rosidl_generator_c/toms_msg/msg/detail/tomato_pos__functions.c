// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from toms_msg:msg/TomatoPos.idl
// generated code does not contain a copyright notice
#include "toms_msg/msg/detail/tomato_pos__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `tomato_data`
#include "toms_msg/msg/detail/tomato_data__functions.h"

bool
toms_msg__msg__TomatoPos__init(toms_msg__msg__TomatoPos * msg)
{
  if (!msg) {
    return false;
  }
  // tomato_data
  if (!toms_msg__msg__TomatoData__Sequence__init(&msg->tomato_data, 0)) {
    toms_msg__msg__TomatoPos__fini(msg);
    return false;
  }
  return true;
}

void
toms_msg__msg__TomatoPos__fini(toms_msg__msg__TomatoPos * msg)
{
  if (!msg) {
    return;
  }
  // tomato_data
  toms_msg__msg__TomatoData__Sequence__fini(&msg->tomato_data);
}

bool
toms_msg__msg__TomatoPos__are_equal(const toms_msg__msg__TomatoPos * lhs, const toms_msg__msg__TomatoPos * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // tomato_data
  if (!toms_msg__msg__TomatoData__Sequence__are_equal(
      &(lhs->tomato_data), &(rhs->tomato_data)))
  {
    return false;
  }
  return true;
}

bool
toms_msg__msg__TomatoPos__copy(
  const toms_msg__msg__TomatoPos * input,
  toms_msg__msg__TomatoPos * output)
{
  if (!input || !output) {
    return false;
  }
  // tomato_data
  if (!toms_msg__msg__TomatoData__Sequence__copy(
      &(input->tomato_data), &(output->tomato_data)))
  {
    return false;
  }
  return true;
}

toms_msg__msg__TomatoPos *
toms_msg__msg__TomatoPos__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__msg__TomatoPos * msg = (toms_msg__msg__TomatoPos *)allocator.allocate(sizeof(toms_msg__msg__TomatoPos), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(toms_msg__msg__TomatoPos));
  bool success = toms_msg__msg__TomatoPos__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
toms_msg__msg__TomatoPos__destroy(toms_msg__msg__TomatoPos * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    toms_msg__msg__TomatoPos__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
toms_msg__msg__TomatoPos__Sequence__init(toms_msg__msg__TomatoPos__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__msg__TomatoPos * data = NULL;

  if (size) {
    data = (toms_msg__msg__TomatoPos *)allocator.zero_allocate(size, sizeof(toms_msg__msg__TomatoPos), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = toms_msg__msg__TomatoPos__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        toms_msg__msg__TomatoPos__fini(&data[i - 1]);
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
toms_msg__msg__TomatoPos__Sequence__fini(toms_msg__msg__TomatoPos__Sequence * array)
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
      toms_msg__msg__TomatoPos__fini(&array->data[i]);
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

toms_msg__msg__TomatoPos__Sequence *
toms_msg__msg__TomatoPos__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__msg__TomatoPos__Sequence * array = (toms_msg__msg__TomatoPos__Sequence *)allocator.allocate(sizeof(toms_msg__msg__TomatoPos__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = toms_msg__msg__TomatoPos__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
toms_msg__msg__TomatoPos__Sequence__destroy(toms_msg__msg__TomatoPos__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    toms_msg__msg__TomatoPos__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
toms_msg__msg__TomatoPos__Sequence__are_equal(const toms_msg__msg__TomatoPos__Sequence * lhs, const toms_msg__msg__TomatoPos__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!toms_msg__msg__TomatoPos__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
toms_msg__msg__TomatoPos__Sequence__copy(
  const toms_msg__msg__TomatoPos__Sequence * input,
  toms_msg__msg__TomatoPos__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(toms_msg__msg__TomatoPos);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    toms_msg__msg__TomatoPos * data =
      (toms_msg__msg__TomatoPos *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!toms_msg__msg__TomatoPos__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          toms_msg__msg__TomatoPos__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!toms_msg__msg__TomatoPos__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
