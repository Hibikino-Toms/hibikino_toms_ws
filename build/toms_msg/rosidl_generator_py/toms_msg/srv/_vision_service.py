# generated from rosidl_generator_py/resource/_idl.py.em
# with input from toms_msg:srv/VisionService.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_VisionService_Request(type):
    """Metaclass of message 'VisionService_Request'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('toms_msg')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'toms_msg.srv.VisionService_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__vision_service__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__vision_service__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__vision_service__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__vision_service__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__vision_service__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class VisionService_Request(metaclass=Metaclass_VisionService_Request):
    """Message class 'VisionService_Request'."""

    __slots__ = [
        '_task',
        '_direction',
    ]

    _fields_and_field_types = {
        'task': 'string',
        'direction': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.task = kwargs.get('task', str())
        self.direction = kwargs.get('direction', str())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.task != other.task:
            return False
        if self.direction != other.direction:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def task(self):
        """Message field 'task'."""
        return self._task

    @task.setter
    def task(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'task' field must be of type 'str'"
        self._task = value

    @builtins.property
    def direction(self):
        """Message field 'direction'."""
        return self._direction

    @direction.setter
    def direction(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'direction' field must be of type 'str'"
        self._direction = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_VisionService_Response(type):
    """Metaclass of message 'VisionService_Response'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('toms_msg')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'toms_msg.srv.VisionService_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__vision_service__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__vision_service__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__vision_service__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__vision_service__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__vision_service__response

            from toms_msg.msg import TomatoPos
            if TomatoPos.__class__._TYPE_SUPPORT is None:
                TomatoPos.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class VisionService_Response(metaclass=Metaclass_VisionService_Response):
    """Message class 'VisionService_Response'."""

    __slots__ = [
        '_detect_check',
        '_target_pos',
    ]

    _fields_and_field_types = {
        'detect_check': 'boolean',
        'target_pos': 'toms_msg/TomatoPos',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['toms_msg', 'msg'], 'TomatoPos'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.detect_check = kwargs.get('detect_check', bool())
        from toms_msg.msg import TomatoPos
        self.target_pos = kwargs.get('target_pos', TomatoPos())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.detect_check != other.detect_check:
            return False
        if self.target_pos != other.target_pos:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def detect_check(self):
        """Message field 'detect_check'."""
        return self._detect_check

    @detect_check.setter
    def detect_check(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'detect_check' field must be of type 'bool'"
        self._detect_check = value

    @builtins.property
    def target_pos(self):
        """Message field 'target_pos'."""
        return self._target_pos

    @target_pos.setter
    def target_pos(self, value):
        if __debug__:
            from toms_msg.msg import TomatoPos
            assert \
                isinstance(value, TomatoPos), \
                "The 'target_pos' field must be a sub message of type 'TomatoPos'"
        self._target_pos = value


class Metaclass_VisionService(type):
    """Metaclass of service 'VisionService'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('toms_msg')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'toms_msg.srv.VisionService')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__vision_service

            from toms_msg.srv import _vision_service
            if _vision_service.Metaclass_VisionService_Request._TYPE_SUPPORT is None:
                _vision_service.Metaclass_VisionService_Request.__import_type_support__()
            if _vision_service.Metaclass_VisionService_Response._TYPE_SUPPORT is None:
                _vision_service.Metaclass_VisionService_Response.__import_type_support__()


class VisionService(metaclass=Metaclass_VisionService):
    from toms_msg.srv._vision_service import VisionService_Request as Request
    from toms_msg.srv._vision_service import VisionService_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
