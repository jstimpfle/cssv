"""wsl.schema: python class representing WSL database schema"""

import wsl.datatype

def u(bin):
    try:
        return bin.decode('utf-8')
    except UnicodeDecodeError:
        s = bin.decode('utf-8', 'backslashreplace')
        raise Exception('Not valid UTF-8: "%s"' % (s,))

def uj(bins):
    return ' '.join(u(bin) for bin in bins)

def isvariable(v):
    return len(v) != 0 and v[0:1].isalpha() and v.isalnum()

class Schema:
    """Schema information for a WSL database.

    Attributes:
        spec: bytes object containing the textual representation of the schema.
            This is normally the string that the schema object was parsed from.

        domains: set object, holding the identifiying names of all the domains
            used in this schema.
        relations: set object, holding the identifiying names of all the
            relations used in this schema.
        keys: set object, holding the identifying names of all the keys used
            in this schema.
        references: set object, holding the identifying names of all the
            references used in this schema.

        spec_of_domain: bytes object containing the textual specification of
            each domain identified by the names in the *domains* attribute.  It
            is guaranteed to be a single line (including the terminating
            newline character).
        spec_of_relation: bytes object containing the textual specification of
            each relation identified by the names in the *relations* attribute.
            It is guaranteed to be a single line (including the terminating
            newline character).
        spec_of_key: bytes object containing the textual representation of each
            key identified by the names in the *keys* attribute.  It is
            guaranteed to be a single line (including the terminating newline
            character).
        spec_of_reference: bytes object containing the textual representation
            of each reference identified by the names in the *references*
            attribute. It is guaranteed to be a single line (including the
            terminating newline character).

        datatype_of_domain: dict object, mapping each domain name from the
            *domains* attribute to a list of the *datatype* objects
            corresponding to the columns of that relation (in order).
        domains_of_relation: dict object, mapping each relation name from the
            *relations* attribute to a list of domain names which represent the
            names of the columns of that relation (in order).
        tuple_of_key: dict object, mapping each key name from the *keys*
            attribute to a tuple *(relation name, 0-based column indices)*.
            This represents the specification of the key.
        tuple_of_reference: dict object, mapping each reference name from the
            *reference* attribute to a tuple *(relation name, column indices,
            relation name, column indices)*. This represents the reference
            constraint as (compatible) keys in the local and foreign relation.
    """
    def __init__(self, spec,
            domains, relations, keys, references,
            spec_of_relation, spec_of_domain, spec_of_key, spec_of_reference,
            domains_of_relation, datatype_of_domain, tuple_of_key, tuple_of_reference):
        self.spec = spec
        self.domains = domains
        self.relations = relations
        self.keys = keys
        self.references = references
        self.spec_of_relation = spec_of_relation
        self.spec_of_domain = spec_of_domain
        self.spec_of_key = spec_of_key
        self.spec_of_reference = spec_of_reference
        self.domains_of_relation = domains_of_relation
        self.datatype_of_domain = datatype_of_domain
        self.tuple_of_key = tuple_of_key
        self.tuple_of_reference = tuple_of_reference

    def __str__(self):
        return """
            domains: %s
            relations: %s
            keys: %s
            references: %s
            spec_of_relation: %s
            spec_of_domain: %s
            spec_of_key: %s
            spec_of_reference: %s
            domains_of_relation: %s
            datatype_of_domain: %s
            tuple_of_key: %s
            tuple_of_reference: %s
        """ %(
        self.domains,
        self.relations,
        self.keys,
        self.references,
        self.spec_of_relation,
        self.spec_of_domain,
        self.spec_of_key,
        self.spec_of_reference,
        self.domains_of_relation,
        self.datatype_of_domain,
        self.tuple_of_key,
        self.tuple_of_reference)

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
        raise Exception('Datatype "%s" not available while parsing DOMAIN declaration' %(u(name),))
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
        raise Exception('Could not parse "%s" as REFERENCE constraint' %(u(line),))
    ld, fd = parts[0].strip(), parts[1].strip()
    name = line  # XXX
    rel1, vs1 = parse_logic_tuple(ld)
    rel2, vs2 = parse_logic_tuple(fd)
    return name, rel1, vs1, rel2, vs2

def parse_schema(schemastring, datatype_parsers):
    if datatype_parsers is None:
        datatype_parsers = dict(wsl.datatype.default_datatype_parsers)
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
            raise Exception('Failed to parse line: %s' %(line,))
        decl, rest = ws
        if decl in [b'DOMAIN', b'TABLE']:
            ws2 = rest.split(None, 1)
            if len(ws2) != 2:
                raise Exception('Failed to parse line: %s' %(line,))
            name, rest2 = ws2
            if decl == b'DOMAIN':
                if name in domains:
                    raise Exception('Table "%s" already declared' %(u(name),))
                domains.add(name)
                spec_of_domain[name] = rest2
            elif decl == b'TABLE':
                if name in relations:
                    raise Exception('Table "%s" already declared' %(u(name),))
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
        dt = parse_domain_decl(domain, spec, datatype_parsers)
        datatype_of_domain[domain] = dt
    for relation in relations:
        spec = spec_of_relation[relation]
        doms = spec.split()
        for dom in doms:
            if dom not in doms:
                raise Exception('Declaration of table "%s" references unknown domain "%s"' %(u(relation), u(dom)))
        domains_of_relation[relation] = doms
    for key in keys:
        spec = spec_of_key[key]
        name, rel, vs = parse_key_decl(spec)
        ix = []
        if rel not in relations:
            raise Exception('No such table: "%s" while parsing KEY constraint "%s"' %(u(rel), u(spec)))
        if len(vs) != len(domains_of_relation[rel]):
            raise Exception('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(u(rel), u(spec)))
        for i, v in enumerate(vs):
            if isvariable(v):
                if v in ix:
                    raise Exception('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
                ix.append(i)
            elif v != b'*':
                raise Exception('Invalid variable "%s" while REFERENCE constraint "%s"' %(u(v), u(name)))
        tuple_of_key[name] = rel, ix
    for reference in references:
        spec = spec_of_reference[reference]
        name, rel1, vs1, rel2, vs2 = parse_reference_decl(spec)
        ix1, ix2 = {}, {}
        for (rel, vs, ix) in [(rel1,vs1,ix1), (rel2,vs2,ix2)]:
            if rel not in relations:
                raise Exception('No such table: "%s" while parsing REFERENCE constraint "%s"' %(u(rel), u(name)))
            if len(vs) != len(domains_of_relation[rel]):
                raise Exception('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(u(rel), u(name)))
            for i, v in enumerate(vs):
                if isvariable(v):
                    if v in ix:
                        raise Exception('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
                    ix[v] = i
                elif v != b'*':
                    raise Exception('Invalid variable "%s" while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
        if sorted(ix1.keys()) != sorted(ix2.keys()):
            raise Exception('Different variables used on both sides of "=>" while parsing REFERENCE constraint "%s"' %(u(name),))
        is1 = [i for _, i in sorted(ix1.items())]
        is2 = [i for _, i in sorted(ix2.items())]
        tuple_of_reference[name] = rel1, is1, rel2, is2

    return Schema(schemastring,
                  domains, relations, keys, references,
                  spec_of_relation, spec_of_domain, spec_of_key, spec_of_reference,
                  domains_of_relation, datatype_of_domain, tuple_of_key, tuple_of_reference)

def make_datatypes_of_relation(schema):
    """Given a schema object, make a direct mapping from each of the schema's
    relations to the datatypes associated with that relation's columns.
    """
    return dict((rel, [schema.datatype_of_domain[d] for d in schema.domains_of_relation[rel]]) for rel in schema.relations)

def embed(schemastring):
    """Prepare a schema for inline inclusion

    Args:
        schemastring: bytes object holding the textual schema representation

    Returns:
        The input schema string with each line prepended with '% '
    """
    return b''.join(b'% ' + line + b'\n' for line in schemastring.split(b'\n'))
