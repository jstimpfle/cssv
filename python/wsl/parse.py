"""Module wsl.parse: Functionality for parsing the rows of a WSL database given schema
information."""

import wsl

def u(bin):
    try:
        return bin.decode('utf-8')
    except UnicodeDecodeError:
        s = bin.decode('utf-8', 'backslashreplace')
        raise Exception('Not valid UTF-8: "%s"' %(s,))

def uj(bins):
    return ' '.join(u(bin) for bin in bins)

def isvariable(v):
    return len(v) != 0 and v[0:1].isalpha() and v.isalnum()

class Ahead:
    def __init__(self, iter):
        assert hasattr(iter, '__next__')
        self.iter = iter
        self.x = None
    def unget(self, x):
        assert self.x is None
        self.x = x
    def __next__(self):
        if self.x is not None:
            out = self.x
            self.x = None
            self.hasx = False
            return out
        return next(self.iter)
    def __iter__(self):
        return self

def split_header(ahead):
    """Given an *Ahead* buffer, consumes the lines which comprise the inline
    database header (if any) and returns them as a single bytes-string.

    Args:
        ahead: An Ahead instance

    Returns:
        the database header which is comprised of the initial lines starting
        with a % character.

    Raises:
        Exception: any exceptions raised from the lines iterator underlying the
            Ahead are not catched; they bubble up to the caller.
        
    """
    schlines = []
    for line in ahead:
        line = line.strip()
        if line:
            if not line.startswith(b'%'):
                ahead.unget(line)
                break
            schlines.append(line.lstrip(b'% '))
    sch = b''.join(l+b'\n' for l in schlines)
    return sch

def parse_domain_decl(name, line, datatype_parsers):
    """Parse a domain declaration line.

    Args:
        name: Name for the resulting domain
        line: Bytes object containing the specification of the datatype.
        datatype_parsers: dict mapping datatype parser names to datatype parsers.

    Returns:
        The parsed datatype.

    Raises:
        Exception: If the parse failed
    """
        
    ws = line.split(None, 1)
    meta, param = ws[0], ws[1] if len(ws) == 2 else b''
    parser = datatype_parsers.get(meta)
    if parser is None:
        raise wsl.ParseError('Datatype "%s" not available while parsing DOMAIN declaration' %(u(name),))
    dt = parser(param)
    return dt

def parse_logic_tuple(line):
    ws = line.split()
    return ws[0], ws[1:]

def parse_key_decl(line):
    """Parse a key constraint declaration.

    Args:
        line: A bytes object, holding a key declaration (without the
            leading KEY keyword) on a single line

    Returns:
        A 3-tuple (name, relation, variables) consisting of an identifying name
        (currently just the line itself), the relation on which the key
        constraint is placed, and the variables or * characters split into a list
    """
    name = line  # XXX
    rel, vs = parse_logic_tuple(line)
    return name, rel, vs

def parse_reference_decl(line):
    """Parse a reference constraint declaration.

    Args:
        line: A bytes object, holding a reference declaration (without the leading
            REFERENCE keyword)

    Returns:
        a 5-tuple (name, relation1, variables1, relation2, variables2) which
        consists of an identifying name for the constraint (currently just the line
        itself), and the local and foreign relation names and variable lists
    """
    line = line.strip()
    parts = line.split(b'=>')
    if len(parts) != 2:
        raise wsl.ParseError('Could not parse "%s" as REFERENCE constraint' %(u(line),))
    ld, fd = parts[0].strip(), parts[1].strip()
    name = line  # XXX
    rel1, vs1 = parse_logic_tuple(ld)
    rel2, vs2 = parse_logic_tuple(fd)
    return name, rel1, vs1, rel2, vs2

def parse_schema(schemastring, datatype_parsers):
    if datatype_parsers is None:
        datatype_parsers = dict(wsl.builtin_datatype_parsers)
    else:
        datatype_parsers = dict(datatype_parsers)

    domains = set()
    relations = set() 
    keys = set() 
    references = set() 
    spec_of_relation = {} 
    spec_of_domain = {} 
    spec_of_key = {} 
    spec_of_reference = {} 
    domains_of_relation = {} 
    datatype_of_domain = {} 
    tuple_of_key = {} 
    tuple_of_reference = {} 

    for line in schemastring.splitlines():
        line = line.strip()
        if not line:
            continue
        ws = line.split(None, 1)
        if len(ws) != 2:
            raise wsl.ParseError('Failed to parse line: %s' %(line,))
        decl, rest = ws
        if decl in [b'DOMAIN', b'TABLE']:
            ws2 = rest.split(None, 1)
            if len(ws2) != 2:
                raise wsl.ParseError('Failed to parse line: %s' %(line,))
            name, rest2 = ws2
            if decl == b'DOMAIN':
                if name in domains:
                    raise wsl.ParseError('Table "%s" already declared' %(u(name),))
                domains.add(name)
                spec_of_domain[name] = rest2
            elif decl == b'TABLE':
                if name in relations:
                    raise wsl.ParseError('Table "%s" already declared' %(u(name),))
                relations.add(name)
                spec_of_relation[name] = rest2
        elif decl == b'KEY':
            name = rest  # XXX
            keys.add(name)
            spec_of_key[name] = rest
        elif decl == b'REFERENCE':
            name = rest  # XXX
            references.add(name)
            spec_of_reference[name] = rest
        else:
            pass  # XXX

    for domain in domains:
        spec = spec_of_domain[domain]
        e, r = parse_domain_decl(domain, spec, datatype_parsers)
        if e != wsl.PARSE_OK:
            raise wsl.ParseError('Failed to parse datatype from %s: %s' %(spec, r or '(unknown reason)'))
        datatype_of_domain[domain] = r
    for relation in relations:
        spec = spec_of_relation[relation]
        doms = spec.split()
        for dom in doms:
            if dom not in doms:
                raise wsl.ParseError('Declaration of table "%s" references unknown domain "%s"' %(u(relation), u(dom)))
        domains_of_relation[relation] = doms
    for key in keys:
        spec = spec_of_key[key]
        name, rel, vs = parse_key_decl(spec)
        ix = []
        if rel not in relations:
            raise wsl.ParseError('No such table: "%s" while parsing KEY constraint "%s"' %(u(rel), u(spec)))
        if len(vs) != len(domains_of_relation[rel]):
            raise wsl.ParseError('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(u(rel), u(spec)))
        for i, v in enumerate(vs):
            if isvariable(v):
                if v in ix:
                    raise wsl.ParseError('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
                ix.append(i)
            elif v != b'*':
                raise wsl.ParseError('Invalid variable "%s" while REFERENCE constraint "%s"' %(u(v), u(name)))
        tuple_of_key[name] = rel, ix
    for reference in references:
        spec = spec_of_reference[reference]
        name, rel1, vs1, rel2, vs2 = parse_reference_decl(spec)
        ix1, ix2 = {}, {}
        for (rel, vs, ix) in [(rel1,vs1,ix1), (rel2,vs2,ix2)]:
            if rel not in relations:
                raise wsl.ParseError('No such table: "%s" while parsing REFERENCE constraint "%s"' %(u(rel), u(name)))
            if len(vs) != len(domains_of_relation[rel]):
                raise wsl.ParseError('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(u(rel), u(name)))
            for i, v in enumerate(vs):
                if isvariable(v):
                    if v in ix:
                        raise wsl.ParseError('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
                    ix[v] = i
                elif v != b'*':
                    raise wsl.ParseError('Invalid variable "%s" while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
        if sorted(ix1.keys()) != sorted(ix2.keys()):
            raise wsl.ParseError('Different variables used on both sides of "=>" while parsing REFERENCE constraint "%s"' %(u(name),))
        is1 = [i for _, i in sorted(ix1.items())]
        is2 = [i for _, i in sorted(ix2.items())]
        tuple_of_reference[name] = rel1, is1, rel2, is2

    return wsl.Schema(schemastring,
         domains, relations, keys, references,
         spec_of_relation, spec_of_domain, spec_of_key, spec_of_reference,
         datatype_of_domain, domains_of_relation, tuple_of_key, tuple_of_reference)

def parse_atom(line, i):
    """Parse an atom literal from *line* starting from *i*.

    Args:
        line: Input bytes string.
        i: Index of the first character to consume in *line*.

    Returns:
        A tuple *(value, j)* which holds the result of the parse and the index
        of the first unconsumed character in *line*.

    Raises:
        Exception: if the parse failed.
    """
    end = len(line)
    x = i
    while i < end and line[i] > 0x20 and line[i] != 0x7f:
        i += 1
    if x == i:
        raise wsl.ParseError('EOL or invalid character while expecting atom at byte %d in line "%s"' %(i, u(line)))
    return line[x:i], i

def parse_string(line, i):
    """Parses a string literal from *line* starting from *i*.

    Args:
        line: Input bytes string.
        i: Index of the first character to consume in *line*.

    Returns:
        A tuple *(value, j)* which holds the result of the parse and the index
        of the first unconsumed character in *line*.

    Raises:
        Exception: if the parse failed.
    """
    end = len(line)
    if i == end or line[i] != 0x5b:
        raise wsl.ParseError('Did not find expected string at byte %d in line %s' %(i, u(line)))
    i += 1
    x = i
    while i < end and line[i] != 0x5d:
        i += 1
    if i == end:
        raise wsl.ParseError('EOL while looking for closing quote in line %s' %(u(line),))
    return line[x:i], i+1

def parse_space(line, i):
    """Parse a space that separates two tokens in a database tuple line.

    This function parses expects precisely one space character, and throws an
    exception if the space is not found.

    Args:
        line: A bytes string which holds a line that represents a database tuple.
        i: An index into the line where the space is supposed to be.

    Returns:
        If the parse succeed, the index of the next character following the space.

    Raises:
        Exception: If no space is found.
    """
    end = len(line)
    if i == end or line[i] != 0x20:
        raise Exception('Expected space character in line %s at position %d' %(u(line), i))
    return i+1

def parse_values(line, i, datatypes):
    """Parse values from line according to *datatypes*, separated by single spaces.
    """
    end = len(line)
    vs = []
    for dt in datatypes:
        i = parse_space(line, i)
        e, r = dt.decode(line, i)
        if e != wsl.PARSE_OK:
            raise Exception('Failed to parse value at byte %d in line %s: %s' %(i, line, r or '(unknown reason)'))
        val, i = r
        vs.append(val)
    if i != end:
        raise Exception('Expected EOL at byte %d in line %s' %(i, u(line)))
    return tuple(vs)

def parse_row(line, datatypes_of_relation):
    """Parse a database tuple (consisting of a predicate name and according
    values).

    Args:
        line: Input bytes string, which must be a line (should not contain
            newline characters).
        datatypes_of_relation: A dict mapping relation names to the list of
            the datatypes of their according columns.

    Returns:
        A 2-tuple (relation, values) consisting of a relation name and another
        tuple holding the parsed values.

    Raises:
        Exception: if the parse failed.
    """
    end = len(line)
    relation, i = parse_atom(line, 0)
    datatypes = datatypes_of_relation.get(relation)
    if datatypes is None:
        raise Exception('No such table: "%s" while parsing line: %s' %(u(relation), u(line)))
    values = parse_values(line, i, datatypes)
    return relation, values

def parse_db(lines, schemastring=None, datatype_parsers=None):
    """Convenience def to parse a WSL database.

    Args:
        lines: An iterator over the lines of the database. The lines must be
            *bytes* objects. *str* strings are not supported.
        schemastring: Optional extern schema specification. If None is given,
            the schema is expected to be given inline (each line prefixed with
            *%*)
        datatype_parsers: Optional datatype-declaration parsers for the
            datatypes used in the database. If None is given, only the
            built-in datatypes (wsl.builtin_datatype_parsers) are
            available.

    Returns:
        A 2-tuple (schema, tuples_of_relation) consisting of the parsed schema
        and a dict mapping each relation name (in schema.relations) to a list
        of database tuples.

    Raises:
        Exception: if the parse failed. Exceptions thrown from the underlying
            lines iterator also bubble up to the caller.
    """
    lookahead = Ahead(lines)

    if schemastring is None:
        schemastring = split_header(lookahead)
    schema = parse_schema(schemastring, datatype_parsers)

    tuples_of_relation = dict()
    for relation in schema.relations:
        tuples_of_relation[relation] = []
    for line in lookahead:
        line = line.strip()
        if line:
            r, tup = parse_row(line, schema.datatypes_of_relation)
            tuples_of_relation[r].append(tup)

    return schema, tuples_of_relation

def parse_db_file(filepath, schemastring=None, datatype_parsers=None):
    """Convenience def for parsing a WSL database from file in the filesystem.

    This opens the file at *filepath* for reading in binary mode, uses the
    resulting file handle to construct an appropriate lines iterator, and
    forwards it and the remaining arguments to *parse_db*.

    Args:
        filepath: Path to the file that contains the database.
        schemastring: See *parse_db()*
        datatype_parsers: See *parse_db()*

    Returns:
        See *parse_db()*

    Raises:
        Exception: Exceptions that result from the filesystem I/O while opening
            or reading the file are not catched; they bubble up to the caller.
    """
    with open(filepath, "rb") as f:
        lines = (line.rstrip(b'\n') for line in f)
        return parse_db(lines, schemastring, datatype_parsers)
