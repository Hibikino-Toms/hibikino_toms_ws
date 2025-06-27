// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from toms_msg:msg/TomatoData.idl
// generated code does not contain a copyright notice
#include "toms_msg/msg/detail/tomato_data__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
toms_msg__msg__TomatoData__init(toms_msg__msg__TomatoData * msg)
{
  if (!msg) {
    return false;
  }
  // x
  // y
  // z
  // approach_direction
  return true;
}

void
toms_msg__msg__TomatoData__fini(toms_msg__msg__TomatoData * msg)
{
  if (!msg) {
    return;
  }
  // x
  // y
  // z
  // approach_direction
}

bool
toms_msg__msg__TomatoData__are_equal(const toms_msg__msg__TomatoData * lhs, const toms_msg__msg__TomatoData * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // x
  if (lhs->x != rhs->x) {
    return false;
  }
  // y
  if (lhs->y != rhs->y) {
    return false;
  }
  // z
  if (lhs->z != rhs->z) {
    return false;
  }
  // approach_direction
  if (lhs->approach_direction != rhs->approach_direction) {
    return false;
  }
  return true;
}

bool
toms_msg__msg__TomatoData__copy(
  const toms_msg__msg__TomatoData * input,
  toms_msg__msg__TomatoData * output)
{
  if (!input || !output) {
    return false;
  }
  // x
  output->x = input->x;
  // y
  output->y = input->y;
  // z
  output->z = input->z;
  // approach_direction
  output->approach_direction = input->approach_direction;
  return true;
}

toms_msg__msg__TomatoData *
toms_msg__msg__TomatoData__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__msg__TomatoData * msg = (toms_msg__msg__TomatoData *)allocator.allocate(sizeof(toms_msg__msg__TomatoData), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(toms_msg__msg__TomatoData));
  bool success = toms_msg__msg__TomatoData__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
toms_msg__msg__TomatoData__destroy(toms_msg__msg__TomatoData * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    toms_msg__msg__TomatoData__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
toms_msg__msg__TomatoData__Sequence__init(toms_msg__msg__TomatoData__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__msg__TomatoData * data = NULL;

  if (size) {
    data = (toms_msg__msg__TomatoData *)allocator.zero_allocate(size, sizeof(toms_msg__msg__TomatoData), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = toms_msg__msg__TomatoData__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        toms_msg__msg__TomatoData__fini(&data[i - 1]);
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
toms_msg__msg__TomatoData__Sequence__fini(toms_msg__msg__TomatoData__Sequence * array)
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
      toms_msg__msg__TomatoData__fini(&array->data[i]);
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

toms_msg__msg__TomatoData__Sequence *
toms_msg__msg__TomatoData__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  toms_msg__msg__TomatoData__Sequence * array = (toms_msg__msg__TomatoData__Sequence *)allocator.allocate(sizeof(toms_msg__msg__TomatoData__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = toms_msg__msg__TomatoData__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
toms_msg__msg__TomatoData__Sequence__destroy(toms_msg__msg__TomatoData__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    toms_msg__msg__TomatoData__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
toms_msg__msg__TomatoData__Sequence__are_equal(const toms_msg__msg__TomatoData__Sequence * lhs, const toms_msg__msg__TomatoData__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!toms_msg__msg__TomatoData__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
toms_msg__msg__TomatoData__Sequence__copy(
  const toms_msg__msg__TomatoData__Sequence * input,
  toms_msg__msg__TomatoData__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(toms_msg__msg__TomatoData);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    toms_msg__msg__TomatoData * data =
      (toms_msg__msg__TomatoData *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!toms_msg__msg__TomatoData__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          toms_msg__msg__TomatoData__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!toms_msg__msg__TomatoData__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
