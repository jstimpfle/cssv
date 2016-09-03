.. WSL documentation master file, created by
   sphinx-quickstart on Mon Aug 22 16:37:51 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

wsl - library for WSL databases
===============================

This library provides an easy to use API to read and write WSL databases with
built-in and user-defined datatypes.

WSL (whitespace separated literals) is an extremely simple and practical text
serialization format for relational data. It is in many ways a better CSV:

 - Lines are table rows with fixed columns instead of just token lists
 - Parsing returns sanitized values, not only strings (according to the columns of each table)
 - Built-in datatypes: Identifiers, Strings, Enums, Integers
 - Easy to integrate custom datatypes
 - Per-datatype lexical syntax for readable, editable, and hackable databases.
 - Unique and foreign keys supported as defined by WSL

The other goal is to be a better Sqlite whenever the data is small enough to be
scanned completely. For example, many web applications.

 - Well-known benefits of textual storage
 - No fixed set of datatypes -- no additional conversion boilerplate
 - No fixed query language -- no SQL boilerplate and no huge query strings

wsl in 1 minute:
----------------

Read a WSL database from a file with included schema. The built-in datatypes
*Atom* and *String* are used to construct meaningful domains. These domains are
used to define tables. *[Foo Bar]* is the notation for the standard WSL string
type. Its advantage is having separate starting and closing delimiters.

.. code:: text

    $ cat db.wsl
    % DOMAIN Person Atom
    % DOMAIN Comment String
    % TABLE person Person Comment
    % TABLE parent Person Person
    % KEY person P *
    % REFERENCE parent P * => person P *
    % REFERENCE parent * P => person P *
    person foo [Foo Bar]
    parent foo bar

.. code:: python3

    import wsl

    filepath = "db.wsl"
    schema, tables = wsl.parse_db_file(filepath, schemastring=None, datatype_parsers=None)
    print(wsl.check_integrity(schema, tables))
    print(tables['person'])
    print(tables['parent'])

Read a WSL database from a python3 string. Here, the schema is given
separately.

.. code:: python3

    import wsl

    schemastring = """
    DOMAIN Person Atom
    DOMAIN Comment String
    TABLE person Person Comment
    TABLE parent Person Person
    KEY person P *
    REFERENCE parent P * => person P *
    REFERENCE parent * P => person P *
    """

    db = """
    person foo [Foo Bar]
    parent foo bar
    """

    lines = iter(db.splitlines())
    schema, tables = wsl.parse_db(lines, schemastring, datatype_parsers=None)
    print(wsl.check_integrity(schema, tables))
    print(tables['person'])
    print(tables['parent'])

Given a parsed schema and a suitable tables dict, we can encode the database
back to a text string:

.. code:: python3

    txt = wsl.format_db(schema, tables, inline_schema=True)
    print(txt, end='')

User-defined datatypes
----------------------

Custom datatypes are quite easy to add. We need a decoder and an encoder. The
decoder gets the line and the position in that line where a value of that
datatype is supposed to begin. It parses the value and returns it together with
the position of the first unconsumed character. The encoder simply serializes
any given value to a string. Let's make a datatype for base64 encoded data.

.. code:: python3

    import wsl
    import base64
    import binascii

    def base64_decode(line, i):
        end = len(line)
        beg = i
        while i < end and (0x41 <= ord(line[i]) <= 0x5a or 0x61 <= ord(line[i]) <= 0x7a or 0x30 <= ord(line[i]) <= 0x39 or line[i] in ['+','/']):
            i += 1
        if beg == i:
            raise wsl.ParseError('Did not find expected base64 literal at character %d, line "%s"' %(beg, line))
        try:
            v = base64.b64decode(line[beg:i], validate=True)
        except binascii.Error as e:
            raise wsl.ParseError('Failed to parse base64 literal at character %d, line "%s"' %(beg, line))
        return v, i

    def base64_encode(x):
        return base64.b64encode(x).decode('ascii')  # dance the unicode dance :/

Finally, we need another parser which gets DOMAIN directives on a single line
and returns a datatype object (which contains the decoder and the encoder).
This is the place where the datatype can be parameterized. For example, this
parser could be made to understand a language that describes a range of valid
integers, or a string type that is parameterized by a regular expression.

In this example, we don't add any parameterizability. But later, we might want
to specifiy other characters instead of + and /.

.. code:: python3

    def parse_base64_datatype(line):
        """Parser for Base64 datatype declarations.

        No special syntax is recognized. Only the bare "Base64" is allowed.
        # TODO: Allow other characters instead of + and /
        """
        if line:
            raise wsl.ParseError('Construction of Base64 domain does not receive any arguments')
        class Base64Datatype:
            decode = base64_decode
            encode = base64_encode
        return Base64Datatype

Now we can easily parse a database using our custom parser:

.. code:: python3

    schemastring = """\
    DOMAIN Filename String
    DOMAIN Data Base64
    TABLE pic Filename Data
    """

    db = """
    pic [cat.xpm] bGDOgm10Dm+5ZPjfNmuP4kalHWUlqT3ZAK7WdP9QniET60y5aO4WmxDCxZUTD/IKOrC2DTSLSb/tLWkb7AyYfP1oMqdw08AFEVTdl8EEA2xldYPF4FY9WB5N+87Ymmjo7vVMpiFvcMJkZZv0zOQ6eeMpCUH2MoTPrrkTHOHx/yPA2hO32gKnOGpoCZQ7q6wUS/M1oHd6DRu1CyIMeJTAZAQjJz74oYAfr8Qt1GOWVswzLkojZlODE1WcVt8nrfm3+Kj3YNS43g2zNGwf7mb2Z7OZwzMqtQNnCuDJgXN3
    """

    dtparsers = wsl.builtin_datatype_parsers + (('Base64', parse_base64_datatype),)
    lines = iter(db.splitlines())
    schema, tables = wsl.parse_db(lines, schemastring, datatype_parsers=dtparsers)

Contents:

.. toctree::
   :maxdepth: 2
   :imported: True

.. automodule:: wsl
   :members: parse_atom, parse_string, parse_space, parse_row, parse_db, parse_db_file

.. automodule:: wsl.schema
.. autoclass:: wsl.schema.Schema

.. automodule:: wsl.integrity
   :members: check_integrity

.. automodule:: wsl.parse
   :members: parse_atom, parse_string, parse_space, parse_row, parse_db, parse_db_file

.. automodule:: wsl.format
   :members: format_atom, format_string, format_tuple, format_db

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

