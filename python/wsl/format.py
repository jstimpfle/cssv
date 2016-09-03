"""Module wsl.format: Functionality for serialization of WSL databases"""

import wsl

def format_schema(schema, escape=False):
    """Encode a schema object as a WSL schema string.

    Args:
        schema: The schema object
        escape: Whether the resulting string should be escaped for inline
            schema notation.

    Returns:
        A string which is the textual representation of the schema.  Currently,
        this is just the *spec* attribute of the schema object. If
        *escape=True*, each line is prepended with a '% ' sequence, so the
        schema string can be used inline in a text file.
    """
    if escape:
        return ''.join('% ' + line + '\n' for line in schema.spec.splitlines())
    else:
        return schema.spec

def format_atom(token):
    """Encode a WSL atom

    Args:
        token: A string that holds a valid WSL atom value.

    Returns:
        A string holding *token* encoded as a WSL atom literal. If the format
        succeeds, the return value is identical to *token* as per the WSL
        specification.

    Raises:
        wsl.FormatError: If the value isn't a valid atom.
    """
    # XXX
    return token

def format_string(token):
    """Encode a WSL string literal.

    Args:
        token: A string that holds a WSL string.

    Returns:
        A string holding *token* encoded as a WSL string literal.
    """
    end = len(token)
    i = 0
    while i < end:
        if ord(token[i]) == 0x22 or ord(token[i]) < 0x20 or ord(token[i] == 0x7f):
            raise wsl.FormatError('Invalid character %d in token %s' %(token[i], token))
        i += 1
    return '[' + token + ']'

def format_tuple(relation, tup, datatypes):
    """Encode a database tuple as a WSL database row.

    Args:
        relation: Name of the relation this tuple belongs to.
        tup: Tuple, holding values according to the relation given.
        datatypes: Tuple, holding datatype objects according to the relation given.

    Returns:
        A string containing a single line (including the terminating newline
        character).

    Raises:
        wsl.FormatError: if formatting fails.
    """
    x = [relation]
    for val, dt in zip(tup, datatypes):
        token = dt.encode(val)
        x.append(token)
    return ' '.join(x) + '\n'

def format_db(schema, tuples_of_relation, inline_schema):
    """Convenience function for encoding a WSL database.

    Args:
        schema: The schema of the database.
        tuples_of_relation: A dict that maps each relation name in
            *schema.relations* to a list that contains all the rows of that
            relation.

    Returns:
        An iterator yielding chunks of encoded text.
        If *inline_schema* is True, the first chunk is the textual
        representation of the schema, each line being escaped with %
        as required for WSL inline notation.
        Each following yielded chunk is the result of encoding one tuple
        of the database (as returned by *format_row()*).

    Raises:
        wsl.FormatError: if formatting fails.
    """
    lines = []
    for relation in sorted(tuples_of_relation.keys()):
        dts = schema.datatypes_of_relation[relation]
        for tup in sorted(tuples_of_relation[relation]):
            lines.append(format_tuple(relation, tup, dts))
    body = ''.join(lines)
    if inline_schema:
        hdr = format_schema(schema, escape=True)
        return hdr + body
    else:
        return body
