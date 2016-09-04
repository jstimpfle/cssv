"""Module wsl.datatype: Built-in WSL datatypes.

Users can add their own datatypes by providing a parser, following the example
of the built-in ones.

A parser takes a datatype declaration, which is string that must be completely
consumed. It returns a datatype object with *decode* and *encode* member defs
as explained in the following paragraph.

The *decode* member of a datatype object is a function that takes a string and
a start index into the string. It returns a pair *(val, j)* where *val* is the
parsed value and *j* is the position of the first unconsumed character. A
*wsl.ParseError* is raised if the decode fails.

The *encode* member of a datatype object is a function that takes an object of
the type that *decode* returns, and returns a string holding the serialized
value. A *wsl.FormatError* is raised if the encode fails.
"""

import wsl

def parse_atom_datatype(line):
    """Parser for Atom datatype declarations.

    No special syntax is recognized. Only the bare "Atom" is allowed.
    """
    if line:
        raise wsl.ParseError('Construction of Atom domain does not receive any arguments')
    class AtomDatatype:
        decode = atom_decode
        encode = atom_encode
    return AtomDatatype

def parse_string_datatype(line):
    if line:
        raise wsl.ParseError('Construction of String domain does not receive any arguments')
    class StringDatatype:
        decode = string_decode
        encode = string_encode
    return StringDatatype

def parse_integer_datatype(line):
    if line:
        raise wsl.ParseError('Construction of Integer domain does not receive any arguments')
    class IntegerDatatype:
        decode = integer_decode
        encode = integer_encode
    return IntegerDatatype

def parse_enum_datatype(line):
    values = line.split()
    options = list(enumerate(values))
    class EnumDatatype:
        decode = make_enum_decode(options)
        encode = make_enum_encode(options)
    return EnumDatatype

def parse_ipv4_datatype(line):
    if line.strip():
        raise wsl.ParseError('IPv4 domain doesn\'t take any arguments')
    class IPv4:
        decode = ipv4_decode
        encode = ipv4_encode
    return IPv4

def atom_decode(line, i):
    """Value decoder for Atom datatype"""
    end = len(line)
    x = i
    while i < end and ord(line[i]) > 0x20 and ord(line[i]) != 0x7f:
        i += 1
    if x == i:
        raise wsl.ParseError('EOL or invalid character while expecting atom at character %d in line "%s"' %(i+1, line))
    return (line[x:i], i)

def atom_encode(atom):
    """Value encoder for Atom datatype"""
    for c in atom:
        if ord(c) < 0x20 or ord(c) in [0x20, 0x5b, 0x5d, 0x7f]:
            raise ValueError('Disallowed character %c in Atom value: %s' %(c, atom))
    return atom

def string_decode(line, i):
    """Value decoder for String datatype"""
    end = len(line)
    if i == end or ord(line[i]) != 0x5b:
        raise wsl.ParseError('Did not find expected WSL string literal at character %d in line %s' %(i+1, line))
    i += 1
    x = i
    while i < end and ord(line[i]) != 0x5d:
        i += 1
    if i == end:
        raise wsl.ParseError('EOL while looking for closing quote in line %s' %(line))
    return (line[x:i], i+1)

def string_encode(string):
    """Value encoder for String datatype"""
    for c in string:
        if ord(c) < 0x20 or ord(c) in [0x5b, 0x5d, 0x7f]:
            raise ValueError('Disallowed character %c in String value: %s' %(c, string))
    return '[' + string + ']'

def integer_decode(line, i):
    """Value decoder for Integer datatype"""
    end = len(line)
    if i == end or not 0x30 <= ord(line[i]) < 0x40:
        raise wsl.ParseError('Did not find expected integer literal at character %d in line %s' %(i+1, line))
    if ord(line[i]) == 0x30:
        raise wsl.ParseError('Found integer literal starting with zero at character %d in line %s' %(i+1, line))
    n = ord(line[i]) - 0x30
    i += 1
    while i < end and 0x30 <= ord(line[i]) < 0x40:
        n = 10*n + ord(line[i]) - 0x30
        i += 1
    return (n, i)

def integer_encode(integer):
    """Value encoder for Integer datatype"""
    return str(integer)

def make_enum_decode(options):
    def enum_decode(line, i):
        """Value decoder for Enum datatype"""
        end = len(line)
        x = i
        while i < end and 0x21 < ord(line[i]) and ord(line[i]) != 0x7f:
            i += 1
        if x == i:
            raise wsl.ParseError('Did not find expected token at line "%s" character %d' %(line, i))
        token = line[x:i]
        for option in options:
            v, t = option
            if t == token:
                return (option, i)
        raise wsl.ParseError('Invalid token "%s" at line "%s" character %d; valid tokens are %s' %(token, line, i, ','.join(y for x, y in options)))
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
    while i < end and (0x30 <= ord(line[i]) < 0x40 or ord(line[i]) == 0x2e):
        i += 1
    token = line[x:i]
    ws = token.split('.')
    if len(ws) == 4:
        try:
            ip = tuple(map(int, ws))
            for b in ip:
                if b < 0 or b >= 256:
                    raise ValueError()
            return (ip, i)
        except ValueError:
            pass
    raise wsl.ParseError('IPv4 address must be 4-tuple of 1 byte integers (0-255)')

def ipv4_encode(ip):
    try:
        a,b,c,d = ip
        for x in [a,b,c,d]:
            if not 0 <= x < 256:
                raise ValueError()
        return '%d.%d.%d.%d' %ip
    except ValueError as e:
        raise ValueError('Not a valid ip address (need 4-tuple of integers in [0,255])')

builtin_datatype_parsers = (
    ('Atom', parse_atom_datatype),
    ('String', parse_string_datatype),
    ('Enum', parse_enum_datatype),
    ('Integer', parse_integer_datatype),
    ('IPv4', parse_ipv4_datatype)
)
