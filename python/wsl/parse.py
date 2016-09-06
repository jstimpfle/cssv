"""Module wsl.parse: Functionality for parsing the rows of a WSL database given schema
information."""

import wsl

def _isvariable(v):
    return len(v) != 0 and v[0:1].isalpha() and v.isalnum()

class Ahead:
    def __init__(self, iter):
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
    database header (if any) and returns them as a single string.

    Args:
        ahead (wsl.Ahead)

    Returns:
        the database header with the leading % characters stripped off.
    """
    schlines = []
    for line in ahead:
        line = line.strip()
        if line:
            if not line.startswith('%'):
                ahead.unget(line)
                break
            schlines.append(line.lstrip('% '))
    sch = ''.join(l+'\n' for l in schlines)
    return sch

def parse_domain_decl(name, line, datatype_parsers):
    """Parse a domain declaration line.

    Args:
        name (str): name for the resulting domain.
        line (str): contains specification of the datatype to parse.
        datatype_parsers (dict): dict mapping datatype parser names to datatype parsers.

    Returns:
        wsl.datatype: The parsed datatype.

    Raises:
        wsl.ParseError: If the parse failed
    """

    ws = line.split(None, 1)
    meta, param = ws[0], ws[1] if len(ws) == 2 else ''
    parser = datatype_parsers.get(meta)
    if parser is None:
        raise wsl.ParseError('Datatype "%s" not available while parsing DOMAIN declaration' %(name,))
    dt = parser(param)
    return dt

def parse_logic_tuple(line):
    ws = line.split()
    return ws[0], ws[1:]

def parse_key_decl(line):
    """Parse a key constraint declaration.

    Args:
        line (str): holds the key specification to parse (without the leading
            KEY keyword) on a single line

    Returns:
        (str, str, list): A 3-tuple (name, relation, variables) consisting of
        an identifying name (currently just the line itself), the relation on
        which the key constraint is placed, and the variables or * characters split into a list

    Raises:
        wsl.ParseError: If the parse failed
    """
    name = line  # XXX
    rel, vs = parse_logic_tuple(line)
    return name, rel, vs

def parse_reference_decl(line):
    """Parse a reference constraint declaration.

    Args:
        line (str): holds reference declaration (without the leading REFERENCE
            keyword)

    Returns:
        (str, str, list, str, list): a 5-tuple (name, relation1, variables1,
        relation2, variables2) which consists of an identifying name for the
        constraint (currently just the line itself), and the local and foreign
        relation names and variable lists.

    Raises:
        wsl.ParseError: If the parse failed
    """
    line = line.strip()
    parts = line.split('=>')
    if len(parts) != 2:
        raise wsl.ParseError('Could not parse "%s" as REFERENCE constraint' %(line,))
    ld, fd = parts[0].strip(), parts[1].strip()
    name = line  # XXX
    rel1, vs1 = parse_logic_tuple(ld)
    rel2, vs2 = parse_logic_tuple(fd)
    return name, rel1, vs1, rel2, vs2

def parse_schema(schemastr, datatype_parsers):
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

    for line in schemastr.splitlines():
        line = line.strip()
        if not line:
            continue
        ws = line.split(None, 1)
        if len(ws) != 2:
            raise wsl.ParseError('Failed to parse line: %s' %(line,))
        decl, rest = ws
        if decl in ['DOMAIN', 'TABLE']:
            ws2 = rest.split(None, 1)
            if len(ws2) != 2:
                raise wsl.ParseError('Failed to parse line: %s' %(line,))
            name, rest2 = ws2
            if decl == 'DOMAIN':
                if name in domains:
                    raise wsl.ParseError('Table "%s" already declared' %(name,))
                domains.add(name)
                spec_of_domain[name] = rest2
            elif decl == 'TABLE':
                if name in relations:
                    raise wsl.ParseError('Table "%s" already declared' %(name,))
                relations.add(name)
                spec_of_relation[name] = rest2
        elif decl == 'KEY':
            name = rest  # XXX
            keys.add(name)
            spec_of_key[name] = rest
        elif decl == 'REFERENCE':
            name = rest  # XXX
            references.add(name)
            spec_of_reference[name] = rest
        else:
            pass  # XXX

    for domain in domains:
        spec = spec_of_domain[domain]
        dt = parse_domain_decl(domain, spec, datatype_parsers)
        datatype_of_domain[domain] = dt
    for relation in relations:
        spec = spec_of_relation[relation]
        rdoms = spec.split()
        for dom in rdoms:
            if dom not in domains:
                raise wsl.ParseError('Declaration of table "%s" references unknown domain "%s"' %(relation, dom))
        domains_of_relation[relation] = rdoms
    for key in keys:
        spec = spec_of_key[key]
        name, rel, vs = parse_key_decl(spec)
        ix = []
        if rel not in relations:
            raise wsl.ParseError('No such table: "%s" while parsing KEY constraint "%s"' %(rel, spec))
        if len(vs) != len(domains_of_relation[rel]):
            raise wsl.ParseError('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(rel, spec))
        for i, v in enumerate(vs):
            if _isvariable(v):
                if v in ix:
                    raise wsl.ParseError('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(v, name))
                ix.append(i)
            elif v != '*':
                raise wsl.ParseError('Invalid variable "%s" while REFERENCE constraint "%s"' %(v, name))
        tuple_of_key[name] = rel, ix
    for reference in references:
        spec = spec_of_reference[reference]
        name, rel1, vs1, rel2, vs2 = parse_reference_decl(spec)
        ix1, ix2 = {}, {}
        for (rel, vs, ix) in [(rel1,vs1,ix1), (rel2,vs2,ix2)]:
            if rel not in relations:
                raise wsl.ParseError('No such table: "%s" while parsing REFERENCE constraint "%s"' %(rel, name))
            if len(vs) != len(domains_of_relation[rel]):
                raise wsl.ParseError('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(rel, name))
            for i, v in enumerate(vs):
                if _isvariable(v):
                    if v in ix:
                        raise wsl.ParseError('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(v, name))
                    ix[v] = i
                elif v != '*':
                    raise wsl.ParseError('Invalid variable "%s" while parsing REFERENCE constraint "%s"' %(v, name))
        if sorted(ix1.keys()) != sorted(ix2.keys()):
            raise wsl.ParseError('Different variables used on both sides of "=>" while parsing REFERENCE constraint "%s"' %(name,))
        is1 = [i for _, i in sorted(ix1.items())]
        is2 = [i for _, i in sorted(ix2.items())]
        tuple_of_reference[name] = rel1, is1, rel2, is2

    return wsl.Schema(schemastr,
         domains, relations, keys, references,
         spec_of_relation, spec_of_domain, spec_of_key, spec_of_reference,
         datatype_of_domain, domains_of_relation, tuple_of_key, tuple_of_reference)

def parse_relation(line, i):
    end = len(line)
    if not 0x41 <= ord(line[i]) <= 0x5a and not 0x61 <= ord(line[i]) <= 0x7a:
        raise wsl.ParseError('Expected table name at character %d in line "%s"' %(i+1, line))
    x = i
    while i < end and (0x41 <= ord(line[i]) <= 0x5a or 0x61 <= ord(line[i]) <= 0x7a):
        i += 1
    return line[x:i], i

def parse_space(line, i):
    """Parse a space that separates two tokens in a database tuple line.

    This function parses expects precisely one space character, and throws an
    exception if the space is not found.

    Args:
        line (str) : holds a database tuple.
        i (int): An index into the line where the space is supposed to be.

    Returns:
        int: If the parse succeed, the index of the next character following
            the space.

    Raises:
        wsl.ParseError: If no space is found.
    """
    end = len(line)
    if i == end or ord(line[i]) != 0x20:
        raise wsl.ParseError('Expected space character in line %s at position %d' %(line, i))
    return i+1

def parse_values(line, i, datatypes):
    """Parse values from line according to *datatypes*, separated by single spaces.

    Args:
        line (str): holds a database tuple.
        i (int): An index into the line where the space is supposed to be.
        datatypes (tuple of wsl.datatype): Tuple holding the datatypes that are
            expected in this line.
    """
    end = len(line)
    vs = []
    for dt in datatypes:
        i = parse_space(line, i)
        val, i = dt.decode(line, i)
        vs.append(val)
    if i != end:
        raise wsl.ParseError('Expected EOL at character %d in line %s' %(i+1, line))
    return tuple(vs)

def parse_row(line, datatypes_of_relation):
    """Parse a database tuple (consisting of a table name and according values).

    Args:
        line (str): holds a database tuple.
        datatypes_of_relation (dict): maps relation names to the list of the
            datatypes of their according columns.

    Returns:
        (str, tuple): A 2-tuple (relation, values) consisting of a relation
        name and another tuple holding the parsed values.

    Raises:
        wsl.ParseError: if the parse failed.
    """
    end = len(line)
    relation, i = parse_relation(line, 0)
    datatypes = datatypes_of_relation.get(relation)
    if datatypes is None:
        raise wsl.ParseError('No such table: "%s" while parsing line: %s' %(relation, line))
    values = parse_values(line, i, datatypes)
    return relation, values

def parse_db(dbfilepath=None, dblines=None, dbstr=None, schemastr=None, datatype_parsers=None):
    """Convenience def to parse a WSL database.

    This parses the schema (from *schemastr* if given, or else as inline schema
    from *lines*), and then calls *parse_row()* with each line in *lines*.

    Only one of dbfilepath, dblines or dbstr should be given.

    Args:
        dbfilepath (str or bytes): Path to the file that contains the database.
        dblines (iter): An iterator yielding the (str) lines of the database.
            This works for all TextIOBase objects, like sys.stdin or open()ed
            files.
        dbstr (str): A string that holds the database.
        schemastr (str): Optional extern schema specification. If *None* is
            given, the schema is expected to be given inline as part of the
            database (each line prefixed with *%*)
        datatype_parsers (list): Optional datatype-declaration parsers for the
            datatypes used in the database. If None is given, only the
            built-in datatypes (wsl.builtin_datatype_parsers) are
            available.

    Returns:
        (str, dict): A 2-tuple (schema, tuples_of_relation) consisting of the
        parsed schema and a dict mapping each relation name (in
        schema.relations) to a list of database tuples.

    Raises:
        wsl.ParseError: if the parse failed.
    """
    if int(dbfilepath is not None) + int(dblines is not None) + int(dbstr is not None) != 1:
        raise ValueError('parse_db() needs exactly one of dbfilepath, dblines or dbstr')

    if dbfilepath is not None:
        lines = open(filepath, "r", encoding="utf-8", newline='\n')
    if dblines is not None:
        lines = dblines
    if dbstr is not None:
        lines = dbstr.split('\n')

    lookahead = Ahead(iter(lines))

    if schemastr is None:
        schemastr = split_header(lookahead)
    schema = parse_schema(schemastr, datatype_parsers)

    tuples_of_relation = dict()
    for relation in schema.relations:
        tuples_of_relation[relation] = []
    for line in lookahead:
        line = line.strip()
        if line:
            r, tup = parse_row(line, schema.datatypes_of_relation)
            tuples_of_relation[r].append(tup)

    return schema, tuples_of_relation
