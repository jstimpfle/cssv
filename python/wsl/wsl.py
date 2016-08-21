#!/usr/bin/python3

from .datatype import default_datatype_parsers, SYNTAX_ATOM, SYNTAX_STRING
from .schema import parse_schema

def format_atom(token):
    return token

def format_string(token):
    x = token
    # XXX some escaping missing
    x = x.replace(b'\\',b'\\\\')
    x = x.replace(b'"',b'\\"')
    x = b'"' + x + b'"'
    return x

def format_row(relation, row, datatypes):
    x = [relation]
    for val, dt in zip(row, datatypes):
        token = dt.encode(val)
        if dt.syntaxtype == SYNTAX_ATOM:
            x.append(format_atom(token))
        else:
            x.append(format_string(token))
    return b' '.join(x) + b'\n'
