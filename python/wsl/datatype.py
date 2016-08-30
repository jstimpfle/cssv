"""Module wsl.datatype: Built-in WSL datatypes.

Users can add their own datatypes by providing a parser, following the example
of the built-in ones.

A parser takes a datatype declaration, which is a bytes object which must be
completely consumed. If the parse succeeds, the parser returns a pair
*(wsl.PARSE_OK, obj)* where *obj* is a datatype object with *decode* and
*encode* member defs as explained in the following paragraph. If the parse
fails, the parser returns *(wsl.PARSE_ERROR, reason)* instead, where *reason*
is either *None* or a *str* object holding a single-line error message.

The *decode* member of a datatype object is a function that takes a bytes
object and a start index into that object. If the decode succeeds, it returns a
pair *(wsl.PARSE_OK, (val, j))* where *val* is the parsed value and *j* is the
position of the first unconsumed character. If the decode fails, it returns a
pair *(wsl.PARSE_ERROR, reason)* where *reason* is either *None* or a *str*
object holding a single-line error message.

The *encode* member of a datatype object is a function that takes an object of
the type that *decode* returns, and returns a bytes object holding the
serialized value. If (unexpectedly) the conversion fails, a ValueError is
raised. 
"""

import wsl

PARSE_OK = 0
PARSE_ERROR = 1

def _u(bin):
    try:
        return bin.decode('utf-8')
    except UnicodeDecodeError:
        s = bin.decode('utf-8', 'backslashreplace')
        raise Exception('Not valid UTF-8: "%s"' % (s,))

def _uj(bins):
    return ' '.join(_u(bin) for bin in bins)


def parse_atom_datatype(line):
    """Parser for Atom datatype declarations.

    No special syntax is recognized. Only the bare "Atom" is allowed.
    """
    if line:
        return wsl.PARSE_ERROR, 'Construction of Atom domain does not receive any arguments'
    class AtomDatatype:
        decode = atom_decode
        encode = atom_encode
    return wsl.PARSE_OK, AtomDatatype

def parse_string_datatype(line):
    if line:
        return wsl.PARSE_ERROR, 'Construction of String domain does not receive any arguments'
    class StringDatatype:
        decode = string_decode
        encode = string_encode
    return wsl.PARSE_OK, StringDatatype

def parse_integer_datatype(line):
    if line:
        return wsl.PARSE_ERROR, 'Construction of Integer domain does not receive any arguments'
    class IntegerDatatype:
        decode = integer_decode
        encode = integer_encode
    return wsl.PARSE_OK, IntegerDatatype

def parse_enum_datatype(line):
    values = line.split()
    options = list(enumerate(values))
    class EnumDatatype:
        decode = make_enum_decode(options)
        encode = make_enum_encode(options)
    return wsl.PARSE_OK, EnumDatatype

def parse_ipv4_datatype(line):
    if line.strip():
        raise wsl.ParseError('IPv4 domain doesn\'t take any arguments')
    class IPv4:
        decode = ipv4_decode
        encode = ipv4_encode
    return wsl.PARSE_OK, IPv4

builtin_datatype_parsers = (
    (b'Atom', parse_atom_datatype),
    (b'String', parse_string_datatype),
    (b'Enum', parse_enum_datatype),
    (b'Integer', parse_integer_datatype),
    (b'IPv4', parse_ipv4_datatype)
)

def atom_decode(line, i):
    """Value decoder for Atom datatype"""
    end = len(line)
    x = i
    while i < end and line[i] > 0x20 and line[i] != 0x7f:
        i += 1
    if x == i:
        return wsl.PARSE_ERROR, 'EOL or invalid character while expecting atom at byte %d in line "%s"' %(i, _u(line))
    return wsl.PARSE_OK, (line[x:i], i)

def atom_encode(atom):
    """Value encoder for Atom datatype"""
    if not isinstance(atom, bytes):
        raise ValueError('Atom value must be bytes object: %s' %(atom,))
    for c in atom:
        if c < 0x20 or c in [0x20, 0x5b, 0x5d, 0x7f]:
            raise ValueError('Disallowed character %c in Atom value: %s' %(c, atom))
    return atom

def string_decode(line, i):
    """Value decoder for String datatype"""
    end = len(line)
    if i == end or line[i] != 0x5b:
        return wsl.PARSE_ERROR, 'Did not find expected string at byte %d in line %s' %(i, _u(line))
    i += 1
    x = i
    while i < end and line[i] != 0x5d:
        i += 1
    if i == end:
        return wsl.PARSE_ERROR, 'EOL while looking for closing quote in line %s' %(_u(line),)
    return wsl.PARSE_OK, (line[x:i], i+1)

def string_encode(string):
    """Value encoder for String datatype"""
    for c in string:
        if c < 0x20 or c in [0x5b, 0x5d, 0x7f]:
            raise ValueError('Disallowed character %c in String value' %(c, string))
    return b'[' + string + b']'

def integer_decode(line, i):
    """Value decoder for Integer datatype"""
    end = len(line)
    if i == end or not 0x30 <= line[i] < 0x40:
        return wsl.PARSE_ERROR, 'Did not find expected integer literal at byte %d in line %s' %(i, _u(line))
    if line[i] == 0x30:
        return wsl.PARSE_ERROR, 'Found integer literal starting with zero at byte %d in line %s' %(i, _u(line))
    n = line[i] - 0x30
    i += 1
    while i < end and 0x30 <= line[i] < 0x40:
        n = 10*n + line[i] - 0x30
        i += 1
    return wsl.PARSE_OK, (n, i)

def integer_encode(integer):
    """Value encoder for Integer datatype"""
    return bytes(str(integer), 'ascii')

def make_enum_decode(options):
    def enum_decode(line, i):
        """Value decoder for Enum datatype"""
        end = len(line)
        x = i
        while i < end and 0x21 < line[i] and line[i] != 0x7f:
            i += 1
        if x == i:
            return wsl.PARSE_ERROR, 'Did not find expected token at line "%s" byte %d' %(_u(line), i)
        token = line[x:i]
        for option in options:
            v, t = option
            if t == token:
                return wsl.PARSE_OK, (option, i)
        return wsl.PARSE_ERROR, 'Invalid token "%s" at line "%s" byte %d; valid tokens are %s' %(_u(token), _u(line), i, _uj(y for x, y in options))
    return enum_decode

def make_enum_encode(options):
    def enum_encode(value):
        """Value encoder for Enum datatype"""
        i, token = value
        return token
    return enum_encode

def ipv4_decode(line, i):
    end = len(line)
    x = i
    while i < end and (0x30 <= line[i] < 0x40 or line[i] == 0x2e):
        i += 1
    token = line[x:i]
    ws = token.split(b'.')
    if len(ws) == 4:
        try:
            ip = tuple(map(int, ws))
            for b in ip:
                if b < 0 or b >= 256:
                    raise ValueError()
            return wsl.PARSE_OK, (ip, i)
        except ValueError:
            pass
    return wsl.PARSE_ERROR, 'IPv4 address must be 4-tuple of 1 byte integers (0-255)'

def ipv4_encode(ip):
    try:
        a,b,c,d = ip
        for x in [a,b,c,d]:
            if not 0 <= x < 256:
                raise ValueError()
        return bytes('%d.%d.%d.%d' %ip, 'ascii')
    except ValueError as e:
        raise ValueError('Not a valid ip address (need 4-tuple of integers in [0,255])')
