"""wsl.format: Functionality for serialization of WSL databases"""

import wsl.schema
import wsl.datatype

def format_atom(token):
    """Encode a bytes object as a WSL atom.

    Args:
        token: A bytes object which holds a valid atom value.

    Returns:
        A bytes object holding *token* encoded as a WSL atom literal.
        If the format succeeds, the return value is identical to *token* as per
        the WSL specification.

    Raises:
        Exception: If the value isn't a valid atom.
    """
    return token

def format_string(token):
    """Encode a bytes object as a WSL string literal.

    Args:
        token: An arbitrary bytes object.

    Returns:
        A bytes object holding *token* encoded as a WSL string literal.
    """
    x = token
    # XXX some escaping missing
    x = x.replace(b'\\',b'\\\\')
    x = x.replace(b'"',b'\\"')
    x = b'"' + x + b'"'
    return x

def format_tup(relation, tup, datatypes):
    """Encode a database tuple as a WSL database row.

    Args:
        relation: Name of the relation this tuple belongs to.
        tup: Tuple, holding values according to the relation given.
        datatypes: Tuple, holding datatype objects according to the relation given.

    Returns:
        A byte-object containing a single line (including the terminating newline
        character).

    Raises:
        Exception: Exceptions thrown while encoding one of the values in *tup*
            are not catched; they bubble up to the caller.
    """
    x = [relation]
    for val, dt in zip(tup, datatypes):
        token = dt.encode(val)
        if dt.syntaxtype == wsl.datatype.SYNTAX_ATOM:
            x.append(format_atom(token))
        elif dt.syntaxtype == wsl.datatype.SYNTAX_STRING:
            x.append(format_string(token))
        else:
            assert False
    return b' '.join(x) + b'\n'

def format_db(schema, tuples_of_relation, inline_schema):
    """Convenience function for encoding a WSL database.

    Args:
        schema: The schema of the database.
        tuples_of_relation: A dict that maps each relation name in
            *schema.relations* to a list that contains all the rows of that
            relation.

    Returns:
        An iterator yielding chunks of encoded text.
        If inline_schema is True, the first chunk is the textual
        representation of the schema, each line being escaped with %
        as required for WSL inline notation.
        Each following yielded chunk is the result of encoding one tuple
        of the database (as returned by *format_row()*).

    Raises:
        Exception: Any exceptions occurring while encoding (using the functions
            *format_schema()*, *format_atom()*, *format_string()*, or the
            *encode()* static methods of the underlying datatypes), are not
            catched; they bubble up to the caller.
    """
    lines = []
    datatypes_of_relation = wsl.schema.make_datatypes_of_relation(schema)
    for relation in sorted(tuples_of_relation.keys()):
        dts = datatypes_of_relation[relation]
        for tup in sorted(tuples_of_relation[relation]):
            lines.append(format_tup(relation, tup, dts))
    body = b''.join(lines)
    if inline_schema:
        hdr = wsl.schema.embed(schema.spec)
        return hdr + body
    else:
        return body
