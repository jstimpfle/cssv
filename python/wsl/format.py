#!/usr/bin/python3

import wsl.schema
from .datatype import SYNTAX_ATOM, SYNTAX_STRING

def format_atom(token):
    return token

def format_string(token):
    x = token
    # XXX some escaping missing
    x = x.replace(b'\\',b'\\\\')
    x = x.replace(b'"',b'\\"')
    x = b'"' + x + b'"'
    return x

def format_tup(relation, tup, datatypes):
    x = [relation]
    for val, dt in zip(tup, datatypes):
        token = dt.encode(val)
        if dt.syntaxtype == SYNTAX_ATOM:
            x.append(format_atom(token))
        elif dt.syntaxtype == SYNTAX_STRING:
            x.append(format_string(token))
        else:
            assert False
    return b' '.join(x) + b'\n'

def format_db(schema, tuples_of_relation):
    hdr = wsl.schema.embed(schema.spec)
    lines = []
    datatypes_of_relation = wsl.schema.make_datatypes_of_relation(schema)
    for relation in sorted(tuples_of_relation.keys()):
        dts = datatypes_of_relation[relation]
        for tup in sorted(tuples_of_relation[relation]):
            lines.append(format_tup(relation, tup, dts))
    return hdr + b''.join(lines)
