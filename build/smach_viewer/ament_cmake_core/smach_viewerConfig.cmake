# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_smach_viewer_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED smach_viewer_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(smach_viewer_FOUND FALSE)
  elseif(NOT smach_viewer_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(smach_viewer_FOUND FALSE)
  endif()
  return()
endif()
set(_smach_viewer_CONFIG_INCLUDED TRUE)

# output package information
if(NOT smach_viewer_FIND_QUIETLY)
  message(STATUS "Found smach_viewer: 3.0.1 (${smach_viewer_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'smach_viewer' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${smach_viewer_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(smach_viewer_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "ament_cmake_export_dependencies-extras.cmake")
foreach(_extra ${_extras})
  include("${smach_viewer_DIR}/${_extra}")
endforeach()
