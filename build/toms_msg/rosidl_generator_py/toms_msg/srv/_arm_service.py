# generated from rosidl_generator_py/resource/_idl.py.em
# with input from toms_msg:srv/ArmService.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_ArmService_Request(type):
    """Metaclass of message 'ArmService_Request'."""

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
                'toms_msg.srv.ArmService_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__arm_service__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__arm_service__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__arm_service__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__arm_service__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__arm_service__request

            from toms_msg.msg import TomatoData
            if TomatoData.__class__._TYPE_SUPPORT is None:
                TomatoData.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ArmService_Request(metaclass=Metaclass_ArmService_Request):
    """Message class 'ArmService_Request'."""

    __slots__ = [
        '_task',
        '_target',
    ]

    _fields_and_field_types = {
        'task': 'string',
        'target': 'toms_msg/TomatoData',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['toms_msg', 'msg'], 'TomatoData'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.task = kwargs.get('task', str())
        from toms_msg.msg import TomatoData
        self.target = kwargs.get('target', TomatoData())

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
        if self.target != other.target:
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
    def target(self):
        """Message field 'target'."""
        return self._target

    @target.setter
    def target(self, value):
        if __debug__:
            from toms_msg.msg import TomatoData
            assert \
                isinstance(value, TomatoData), \
                "The 'target' field must be a sub message of type 'TomatoData'"
        self._target = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_ArmService_Response(type):
    """Metaclass of message 'ArmService_Response'."""

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
                'toms_msg.srv.ArmService_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__arm_service__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__arm_service__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__arm_service__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__arm_service__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__arm_service__response

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


class ArmService_Response(metaclass=Metaclass_ArmService_Response):
    """Message class 'ArmService_Response'."""

    __slots__ = [
        '_task_comp',
        '_tom_hight',
    ]

    _fields_and_field_types = {
        'task_comp': 'boolean',
        'tom_hight': 'std_msgs/Int32',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Int32'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.task_comp = kwargs.get('task_comp', bool())
        from std_msgs.msg import Int32
        self.tom_hight = kwargs.get('tom_hight', Int32())

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
        if self.task_comp != other.task_comp:
            return False
        if self.tom_hight != other.tom_hight:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def task_comp(self):
        """Message field 'task_comp'."""
        return self._task_comp

    @task_comp.setter
    def task_comp(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'task_comp' field must be of type 'bool'"
        self._task_comp = value

    @builtins.property
    def tom_hight(self):
        """Message field 'tom_hight'."""
        return self._tom_hight

    @tom_hight.setter
    def tom_hight(self, value):
        if __debug__:
            from std_msgs.msg import Int32
            assert \
                isinstance(value, Int32), \
                "The 'tom_hight' field must be a sub message of type 'Int32'"
        self._tom_hight = value


class Metaclass_ArmService(type):
    """Metaclass of service 'ArmService'."""

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
                'toms_msg.srv.ArmService')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__arm_service

            from toms_msg.srv import _arm_service
            if _arm_service.Metaclass_ArmService_Request._TYPE_SUPPORT is None:
                _arm_service.Metaclass_ArmService_Request.__import_type_support__()
            if _arm_service.Metaclass_ArmService_Response._TYPE_SUPPORT is None:
                _arm_service.Metaclass_ArmService_Response.__import_type_support__()


class ArmService(metaclass=Metaclass_ArmService):
    from toms_msg.srv._arm_service import ArmService_Request as Request
    from toms_msg.srv._arm_service import ArmService_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
