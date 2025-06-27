# generated from rosidl_generator_py/resource/_idl.py.em
# with input from toms_msg:srv/CartService.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_CartService_Request(type):
    """Metaclass of message 'CartService_Request'."""

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
                'toms_msg.srv.CartService_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__cart_service__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__cart_service__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__cart_service__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__cart_service__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__cart_service__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class CartService_Request(metaclass=Metaclass_CartService_Request):
    """Message class 'CartService_Request'."""

    __slots__ = [
        '_move_value',
        '_pwm_value',
    ]

    _fields_and_field_types = {
        'move_value': 'int16',
        'pwm_value': 'int16',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int16'),  # noqa: E501
        rosidl_parser.definition.BasicType('int16'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.move_value = kwargs.get('move_value', int())
        self.pwm_value = kwargs.get('pwm_value', int())

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
        if self.move_value != other.move_value:
            return False
        if self.pwm_value != other.pwm_value:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def move_value(self):
        """Message field 'move_value'."""
        return self._move_value

    @move_value.setter
    def move_value(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'move_value' field must be of type 'int'"
            assert value >= -32768 and value < 32768, \
                "The 'move_value' field must be an integer in [-32768, 32767]"
        self._move_value = value

    @builtins.property
    def pwm_value(self):
        """Message field 'pwm_value'."""
        return self._pwm_value

    @pwm_value.setter
    def pwm_value(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'pwm_value' field must be of type 'int'"
            assert value >= -32768 and value < 32768, \
                "The 'pwm_value' field must be an integer in [-32768, 32767]"
        self._pwm_value = value


# Import statements for member types

# already imported above
# import builtins

import math  # noqa: E402, I100

# already imported above
# import rosidl_parser.definition


class Metaclass_CartService_Response(type):
    """Metaclass of message 'CartService_Response'."""

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
                'toms_msg.srv.CartService_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__cart_service__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__cart_service__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__cart_service__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__cart_service__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__cart_service__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class CartService_Response(metaclass=Metaclass_CartService_Response):
    """Message class 'CartService_Response'."""

    __slots__ = [
        '_move_result',
    ]

    _fields_and_field_types = {
        'move_result': 'float',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.move_result = kwargs.get('move_result', float())

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
        if self.move_result != other.move_result:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def move_result(self):
        """Message field 'move_result'."""
        return self._move_result

    @move_result.setter
    def move_result(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'move_result' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'move_result' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._move_result = value


class Metaclass_CartService(type):
    """Metaclass of service 'CartService'."""

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
                'toms_msg.srv.CartService')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__cart_service

            from toms_msg.srv import _cart_service
            if _cart_service.Metaclass_CartService_Request._TYPE_SUPPORT is None:
                _cart_service.Metaclass_CartService_Request.__import_type_support__()
            if _cart_service.Metaclass_CartService_Response._TYPE_SUPPORT is None:
                _cart_service.Metaclass_CartService_Response.__import_type_support__()


class CartService(metaclass=Metaclass_CartService):
    from toms_msg.srv._cart_service import CartService_Request as Request
    from toms_msg.srv._cart_service import CartService_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
