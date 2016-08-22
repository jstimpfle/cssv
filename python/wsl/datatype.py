SYNTAX_ATOM = 0
SYNTAX_STRING = 1

class Datatype:
    """
    A parsed datatype should have the following members:
    """
    syntaxtype = None  # SYNTAX_ATOM or SYNTAX_STRING
    @staticmethod
    def decode(token):
        pass
    @staticmethod
    def encode(value):
        pass

def parse_atom_datatype(line):
    """Parser for Atom datatype declarations

    No special syntax is recognized. Only the bare "Atom" is allowed.
    """
    if line:
        raise Exception('Construction of Atom domain does not receive any arguments')
    class AtomDatatype:
        syntaxtype = SYNTAX_ATOM
        @staticmethod
        def decode(token):
            return token
        @staticmethod
        def encode(value):
            return value
    return AtomDatatype

def parse_string_datatype(line):
    if line:
        raise Exception('Construction of String domain does not receive any arguments')
    class StringDatatype:
        syntaxtype = SYNTAX_STRING
        @staticmethod
        def decode(token):
            return token
        @staticmethod
        def encode(value):
            return value
    return StringDatatype

def parse_integer_datatype(line):
    if line:
        raise Exception('Construction of Integer domain does not receive any arguments')
    class IntegerDatatype:
        syntaxtype = SYNTAX_ATOM
        @staticmethod
        def decode(token):
            try:
                return int(token)
            except ValueError:
                raise Exception('Failed to parse %s as integer' %(u(token),))
        @staticmethod
        def encode(value):
            return bytes(str(value), 'ascii')
    return IntegerDatatype

def parse_enum_datatype(line):
    values = line.split()
    pairs = list(enumerate(values))
    class EnumDatatype:
        syntaxtype = SYNTAX_ATOM
        @staticmethod
        def decode(token):
            for pair in pairs:
                i, v = pair
                if v == token:
                    return pair
            raise Exception('invalid token "%s"; valid tokens are %s' %(u(token), uj(values)))
        @staticmethod
        def encode(value):
            i,token = value
            return token
    return EnumDatatype

def parse_ipv4_datatype(line):
    if line.strip():
        raise Exception('IPv4 domain doesn\'t take any arguments')
    class IPv4:
        syntaxtype = SYNTAX_ATOM
        @staticmethod
        def decode(token):
            ws = token.split(b'.')
            if len(ws) == 4:
                try:
                    ip = tuple(map(int, ws))
                    for b in ip:
                        if b < 0 or b >= 256:
                            raise ValueError()
                    return ip
                except ValueError:
                    pass
            raise Exception('IPv4 address must be 4-tuple of 1 byte integers (0-255)')
        @staticmethod
        def encode(value):
            return bytes('%d.%d.%d.%d' % value, 'ascii')
    return IPv4

default_datatype_parsers = (
    (b'Atom', parse_atom_datatype),
    (b'String', parse_string_datatype),
    (b'Enum', parse_enum_datatype),
    (b'Integer', parse_integer_datatype),
    (b'IPv4', parse_ipv4_datatype)
)
