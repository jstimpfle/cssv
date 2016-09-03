.. WSL documentation master file, created by
   sphinx-quickstart on Mon Aug 22 16:37:51 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

python-wsl - library for WSL databases
======================================

WSL (whitespace separated literals) is a text serialization format for
relational data. This library provides an easy to use and extensible API to
read and write WSL databases.

python-wsl in 1 minute:

.. code:: python

    import wsl

    schemastring = """
    DOMAIN PersonName Atom
    DOMAIN Comment String
    TABLE person Person Comment
    TABLE parent Person Person
    KEY Person P *
    """

    lines = iter(sys.stdin.buffer)
    schema, tables = wsl.parse_db(lines, schemastring, datatype_parsers=None)
    print(tables['person'])
    print(tables['parent'])

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

