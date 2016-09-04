"""Module wsl.format: Functionality for serialization of WSL databases"""

import wsl

def format_schema(schema, escape=False):
    """Encode a schema object as a WSL schema string.

    Args:
        schema (wsl.Schema): The schema object
        escape (bool): Whether the resulting string should be escaped for
            inline schema notation.

    Returns:
        str: The textual representation of the schema. Currently, this is just
        the *spec* attribute of the schema object. If *escape=True*, each line
        is prepended with a '% ' sequence, so the schema string can be used
        inline in a text file.
    """
    if escape:
        return ''.join('% ' + line + '\n' for line in schema.spec.splitlines())
    else:
        return schema.spec


def format_row(relation, tup, encoders):
    """Encode a WSL database row.

    Args:
        relation (str): Name of the relation this tuple belongs to.
        tup (tuple): Values according to the columns of *relation*
        encoders (tuple): Encoders according to the columns of *relation*

    Returns:
        str: A single line (including the terminating newline character).

    Raises:
        wsl.FormatError: if formatting fails.
    """
    x = [relation]
    for val, encode in zip(tup, encoders):
        x.append(encode(val))
    return ' '.join(x) + '\n'

def format_db(schema, tuples_of_relation, inline_schema):
    """Convenience function for encoding a WSL database.

    Args:
        schema (wsl.Schema): The schema of the database.
        tuples_of_relation (dict): A dictionary that maps each relation name in
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
        encoders = []
        for x in schema.domains_of_relation[relation]:
            encoders.append(schema.datatype_of_domain[x].encode)
        for tup in sorted(tuples_of_relation[relation]):
            lines.append(format_row(relation, tup, encoders))
    body = ''.join(lines)
    if inline_schema:
        hdr = format_schema(schema, escape=True)
        return hdr + body
    else:
        return body
