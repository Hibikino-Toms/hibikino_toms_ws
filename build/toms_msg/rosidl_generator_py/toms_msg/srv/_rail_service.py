# generated from rosidl_generator_py/resource/_idl.py.em
# with input from toms_msg:srv/RailService.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_RailService_Request(type):
    """Metaclass of message 'RailService_Request'."""

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
                'toms_msg.srv.RailService_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__rail_service__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__rail_service__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__rail_service__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__rail_service__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__rail_service__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class RailService_Request(metaclass=Metaclass_RailService_Request):
    """Message class 'RailService_Request'."""

    __slots__ = [
        '_req_dir',
    ]

    _fields_and_field_types = {
        'req_dir': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.req_dir = kwargs.get('req_dir', str())

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
        if self.req_dir != other.req_dir:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def req_dir(self):
        """Message field 'req_dir'."""
        return self._req_dir

    @req_dir.setter
    def req_dir(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'req_dir' field must be of type 'str'"
        self._req_dir = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_RailService_Response(type):
    """Metaclass of message 'RailService_Response'."""

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
                'toms_msg.srv.RailService_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__rail_service__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__rail_service__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__rail_service__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__rail_service__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__rail_service__response

            from std_msgs.msg import Int32
            if Int32.__class__._TYPE_SUPPORT is None:
                Int32.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class RailService_Response(metaclass=Metaclass_RailService_Response):
    """Message class 'RailService_Response'."""

    __slots__ = [
        '_res_dir',
        '_pulse',
    ]

    _fields_and_field_types = {
        'res_dir': 'string',
        'pulse': 'std_msgs/Int32',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Int32'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.res_dir = kwargs.get('res_dir', str())
        from std_msgs.msg import Int32
        self.pulse = kwargs.get('pulse', Int32())

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
        if self.res_dir != other.res_dir:
            return False
        if self.pulse != other.pulse:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def res_dir(self):
        """Message field 'res_dir'."""
        return self._res_dir

    @res_dir.setter
    def res_dir(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'res_dir' field must be of type 'str'"
        self._res_dir = value

    @builtins.property
    def pulse(self):
        """Message field 'pulse'."""
        return self._pulse

    @pulse.setter
    def pulse(self, value):
        if __debug__:
            from std_msgs.msg import Int32
            assert \
                isinstance(value, Int32), \
                "The 'pulse' field must be a sub message of type 'Int32'"
        self._pulse = value


class Metaclass_RailService(type):
    """Metaclass of service 'RailService'."""

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
                'toms_msg.srv.RailService')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__rail_service

            from toms_msg.srv import _rail_service
            if _rail_service.Metaclass_RailService_Request._TYPE_SUPPORT is None:
                _rail_service.Metaclass_RailService_Request.__import_type_support__()
            if _rail_service.Metaclass_RailService_Response._TYPE_SUPPORT is None:
                _rail_service.Metaclass_RailService_Response.__import_type_support__()


class RailService(metaclass=Metaclass_RailService):
    from toms_msg.srv._rail_service import RailService_Request as Request
    from toms_msg.srv._rail_service import RailService_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
