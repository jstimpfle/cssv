from .datatype import default_datatype_parsers, SYNTAX_ATOM, SYNTAX_STRING

def u(bin):
    try:
        return bin.decode('utf-8')
    except UnicodeDecodeError:
        s = bin.decode('utf-8', 'backslashreplace')
        raise Exception('Not valid UTF-8: "%s"' % (s,))

def uj(bins):
    return ' '.join(u(bin) for bin in bins)


class Schema:
    def __init__(self, spec,
            domains, relations, keys, references,
            spec_of_relation, spec_of_domain, spec_of_key, spec_of_reference,
            domains_of_relation, datatype_of_domain, tuple_of_key, tuple_of_reference):
        " original textual specification of schema "
        self.spec = spec
        " identities given by textual names "
        self.domains = domains  # set ( domain name )
        self.relations = relations  # set ( relation name )
        self.keys = keys  # set ( key name )
        self.references = references  # set ( reference names )
        " for each identity, associated encoded specification (single line) "
        self.spec_of_relation = spec_of_relation  # table name -> line
        self.spec_of_domain = spec_of_domain  # domain name -> line
        self.spec_of_key = spec_of_key  # key name -> line
        self.spec_of_reference = spec_of_reference  # reference name -> line
        " for each identity, associated decoded specification "
        self.domains_of_relation = domains_of_relation  # table name -> list ( domain name )
        self.datatype_of_domain = datatype_of_domain  # domain name -> datatype object
        self.tuple_of_key = tuple_of_key  # key name -> ( table name, ( 0-based column indices ) )
        self.tuple_of_reference = tuple_of_reference  # reference name -> reference tuple

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
    ws = line.split(None, 1)
    meta, param = ws[0], ws[1] if len(ws) == 2 else b''
    parser = datatype_parsers.get(meta)
    if parser is None:
        raise Exception('Datatype "%s" not available while parsing DOMAIN declaration' %(u(name),))
    dt = parser(param)
    return name, dt

def parse_logic_tuple(line):
    ws = line.split()
    return ws[0], ws[1:]

def parse_key_decl(line):
    name = line  # XXX
    rel, vs = parse_logic_tuple(line)
    return name, rel, vs

def parse_reference_decl(line):
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
        datatype_parsers = dict(default_datatype_parsers)
    else:
        datatype_parsers = dict(datatype_parsers)

    " identities given by textual names "
    domains = set() # set ( domain name )
    relations = set()  # set ( relation name )
    keys = set()  # set ( key name )
    references = set()  # set ( reference names )
    " for each identity, associated encoded specification (single line) "
    spec_of_relation = {}  # table name -> line
    spec_of_domain = {}  # domain name -> line
    spec_of_key = {}  # key name -> line
    spec_of_reference = {}  # reference name -> line
    " for each identity, associated decoded specification "
    domains_of_relation = {}  # table name -> list ( domain name )
    datatype_of_domain = {}  # domain name -> datatype object
    tuple_of_key = {}  # key name -> ( table name, ( 0-based column indices ) )
    tuple_of_reference = {}  # reference name -> reference tuple

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
        name, dt = parse_domain_decl(domain, spec, datatype_parsers)
        datatype_of_domain[name] = dt
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
            if v.isalpha():
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
                if v.isalpha():
                    if v in ix:
                        raise Exception('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
                    ix[v] = i
                elif v != b'*':
                    raise Exception('Invalid variable "%s" while REFERENCE constraint "%s"' %(u(v), u(name)))
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
    return dict((rel, [schema.datatype_of_domain[d] for d in schema.domains_of_relation[rel]]) for rel in schema.relations)

def embed(schemastring):
    return b''.join(b'% ' + line + b'\n' for line in schemastring.split(b'\n'))

if __name__ == '__main__':
    schemastr = b"""
DOMAIN Person Atom
DOMAIN PersonDesc String
DOMAIN Gender Enum male female

TABLE Person Person Gender PersonDesc
TABLE Friends Person Person
TABLE Couple Person Person
    """
    print(parse_schema(schemastr).__dict__)
