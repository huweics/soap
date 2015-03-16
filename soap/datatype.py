from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.linalg import IntegerIntervalArray, ErrorSemanticsArray


class TypeBase(object):
    """The base class of all data types.  """
    def __repr__(self):
        return '<{}>'.format(self)

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash(self.__class__)


class AutoType(TypeBase):
    """Don't care type.  """
    def __str__(self):
        return 'auto'


class BoolType(TypeBase):
    """Boolean data type.  """
    def __str__(self):
        return 'bool'


class IntType(TypeBase):
    """Integer data type.  """
    def __str__(self):
        return 'int'


class RealType(TypeBase):
    """Real data type.  """
    def __str__(self):
        return 'real'


auto_type = AutoType()
bool_type = BoolType()
int_type = IntType()
real_type = RealType()


class ArrayType(TypeBase):
    num_type = None

    def __init__(self, shape):
        super().__init__()
        self.shape = tuple(shape)

    def __str__(self):
        return '{}[{}]'.format(
            self.num_type, ', '.join(str(d) for d in self.shape))

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.num_type == other.num_type and
            self.shape == other.shape)

    def __hash__(self):
        return hash((self.num_type, self.shape))


class IntegerArrayType(ArrayType):
    num_type = int_type


class RealArrayType(ArrayType):
    num_type = real_type


def type_of(value):
    if value is None:
        return
    if isinstance(value, IntegerInterval):
        return int_type
    if isinstance(value, ErrorSemantics):
        return real_type
    if isinstance(value, IntegerIntervalArray):
        return IntegerArrayType(value.shape)
    if isinstance(value, ErrorSemanticsArray):
        return RealArrayType(value.shape)
    raise TypeError('Unrecognized type {}'.format(type(value)))


def cast(dtype, value=None, top=False, bottom=False):
    if dtype == int_type:
        return IntegerInterval(value, top=top, bottom=bottom)
    if dtype == real_type:
        return ErrorSemantics(value, top=top, bottom=bottom)
    if isinstance(dtype, IntegerArrayType):
        cls = IntegerIntervalArray
    elif isinstance(dtype, RealArrayType):
        cls = ErrorSemanticsArray
    else:
        raise TypeError('Do not recognize type.')
    shape = None if value is not None else dtype.shape
    array = cls(value, _shape=shape, top=top, bottom=bottom)
    if shape != array.shape:
        raise ValueError(
            'Array shape is not the same as the shape specified by data type.')
    return array
