#!/usr/bin/python3

from .datatypes import default_datatypes, SYNTAX_ATOM, SYNTAX_STRING

class L1:
    def __init__(self, iter):
        self.iter = iter
        self.hasx = False
    def unget(self, x):
        assert not self.hasx
        self.x = x
        self.hasx = True
    def __next__(self):
        if self.hasx:
            out = self.x
            self.x = None
            self.hasx = False
            return out
        return next(self.iter)
    def __iter__(self):
        return self

def u(bin):
    try:
        return bin.decode('utf-8')
    except UnicodeDecodeError:
        s = bin.decode('utf-8', 'backslashreplace')
        raise Exception('Not valid UTF-8: "%s"' % (s,))

def uj(bins):
    return ' '.join(u(bin) for bin in bins)

class Schema:
    def __init__(self, coldescs, cols, keys, refs):
        self.coldescs = coldescs  # { tablename: [(colname, colspec)] }
        self.cols = cols  # { tablename: [column] }
        self.keys = keys  # { keyname: (table, [column index]) }
        self.refs = refs  # { refname: (table, [column index], table, [column index]) }

def key_from_row(row, ix):
    return tuple(row[i] for i in ix)

class Database:
    def __init__(self, schema):
        self.schema = schema
        self.relvar = {}  # { name: set() }
        self.key_index = {}  # { name: set() }
        self.ref_index = {}  # { name: index of key in foreign table }
        for name in schema.cols:
            self.relvar[name] = set()
        for name in schema.keys:
            self.key_index[name] = set()
        for name in schema.refs:
            self.ref_index[name] = set()

    def add_row(self, table, row):
        if table not in self.relvar:
            raise Exception('No such table: %s' %(table,))
        if len(row) != len(self.schema.cols[table]):
            raise Exception('Can\'t add row %s to table %s: wrong arity' %(u(row), u(table)))
        t = self.relvar[table]
        if row in t:
            raise Exception('Duplicate row %s' %(row,))
        t.add(row)
        for name, (ut, ix) in self.schema.keys.items():
            if ut == table:
                k = key_from_row(row, ix)
                ux = self.key_index[name]
                if k in ux:
                    raise Exception('Unique constraint "%s" violated by row %s %s' %(u(name), u(ut), uj(row)))
                ux.add(k)
        for name, (_, _, ft, fix) in self.schema.refs.items():
            if ft == table:
                k = key_from_row(row, fix)
                fx = self.ref_index[name]
                fx.add(k)

    def check_referential_integrity(self):
        for name, (lt, lix, _, _) in self.schema.refs.items():
            for row in self.relvar[lt]:
                k = key_from_row(row, lix)
                fx = self.ref_index[name]
                if k not in fx:
                    raise Exception('Foreign key constraint "%s" violated by %s %s"' %(u(name), u(lt), uj(row)))

    def dump(self):
        tables = sorted(self.relvar.keys())
        for table in tables:
            cols = self.schema.cols[table]
            for row in sorted(self.relvar[table]):
                yield format_row(table, row, cols)

def parse_datatype(line, parser):
    ws = line.split(None, 1)
    if ws:
        name, rest = ws[0], ws[1] if len(ws) == 2 else b''
        if name not in parser:
            raise Exception('No parser for datatype "%s" available while parsing DOMAIN declaration' %(u(name,)))
        datatype = parser[name](rest)
        return datatype
    raise Exception('Failed to parse %s as datatype declaration' %(u(line),))

def parse_domain(line, datatypes):
    ws = line.split(None, 1)
    if ws:
        name, rest = ws[0], ws[1] if len(ws) == 2 else b''
        datatype = parse_datatype(rest, datatypes)
        return name, datatype
    raise Exception('Could not parse "%s" as DOMAIN declaration' %(u(b' '.join(ws))))

def parse_table(line):
    ws = line.split()
    if len(ws) < 2:
        raise Exception('TABLE declaration syntax: TABLE <name> columns...')
    return (ws[0], ws[1:])

def parse_logic_tuple(line):
    ws = line.split()
    return ws[0], ws[1:]

def parse_key(line):
    name = line  # XXX
    t, vs = parse_logic_tuple(line)
    return name, (t, vs)

def parse_ref(line):
    line = line.strip()
    parts = line.split(b'=>')
    if len(parts) != 2:
        raise Exception('Failed to parse "%s" as REFERENCE constraint' %(u(line),))
    ld, fd = parts[0].strip(), parts[1].strip()
    name = line  # XXX
    lt, lvs = parse_logic_tuple(ld)
    ft, fvs = parse_logic_tuple(fd)
    return name, (lt, lvs, ft, fvs)

def parse_schema(lines, datatypes=None):
    if datatypes is None:
        datatypes = dict(default_datatypes)
    else:
        datatypes = dict(datatypes)
    doms = {}
    tables = {}
    keys = {}
    refs = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        ws = line.split(None, 1)
        if len(ws) != 2:
            ws.append(b'')
        decl, rest = ws
        if decl == b'DOMAIN':
            name, dom = parse_domain(rest, datatypes)
            doms[name] = rest, dom
        if decl == b'TABLE':
            name, tdoms = parse_table(rest)
            if name in tables:
                raise Exception('Table "%s" already declared' %(u(name),))
            tables[name] = tdoms
        if decl == b'KEY':
            name, key = parse_key(line[4:])
            keys[name] = key
        if decl == b'REFERENCE':
            name, ref = parse_ref(line[9:])
            refs[name] = ref

    for table, tdoms in tables.items():
        for dom in tdoms:
            if dom not in doms:
                raise Exception('Declaration of table "%s" references unknown domain "%s"' %(u(table), u(dom)))

    schdescs = {}
    schtables = {}

    for table, tdoms in tables.items():
        schdescs[table] = []
        schtables[table] = []
        for dom in tdoms:
            spec, col = doms[dom]
            schdescs[table].append((dom, spec))
            schtables[table].append(col)

    schkeys = {}
    for name, (table, vars) in keys.items():
        ix = []
        if table not in tables:
            raise Exception('No such table: "%s" while parsing KEY constraint "%s"' %(u(name), u(name)))
        if len(vars) != len(tables[table]):
            raise Exception('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(u(name), u(name)))
        for i, v in enumerate(vars):
            if v != b'*':
                if not v.isalpha():
                    raise Exception('Invalid variable "%s" while parsing "%s" as logic tuple' %(u(v), u(name)))
                ix.append(i)
        schkeys[name] = table, ix

    schrefs = {}
    for name, (lt, lvs, ft, fvs) in refs.items():
        lix, fix = {}, {}
        for (table, vars, ix) in [(lt,lvs,lix), (ft,fvs,fix)]:
            if table not in tables:
                raise Exception('No such table: "%s" while parsing REFERENCE constraint "%s"' %(u(table), u(name)))
            if len(vars) != len(tables[table]):
                raise Exception('Arity mismatch for table "%s" while parsing KEY constraint "%s"' %(u(table), u(name)))
            for i, v in enumerate(vars):
                if v != b'*':
                    if not v.isalpha():
                        raise Exception('Invalid variable "%s" while REFERENCE constraint "%s"' %(u(v), u(name)))
                    if v in ix:
                        raise Exception('Variable "%s" used twice on the same side while parsing REFERENCE constraint "%s"' %(u(v), u(name)))
                    ix[v] = i
        if sorted(lix.keys()) != sorted(fix.keys()):
            raise Exception('Different variables used on both sides of "=>" while parsing REFERENCE constraint "%s"' %(u(name),))
        ll = [i for _, i in sorted(lix.items())]
        ff = [i for _, i in sorted(fix.items())]
        schrefs[name] = lt, ll, ft, ff

    return Schema(schdescs, schtables, schkeys, schrefs)

def hexconvert(c):
    x = ord(c)
    if 48 <= x < 58:
        return x - 48
    if 97 <= x < 103:
        return 10 + x - 97
    return None

def parse_atom(line, i):
    end = len(line)
    x = i
    while i < end and line[i] > 0x20 and line[i] != 0x7f:
        i += 1
    if x == i:
        raise Exception('EOL or invalid character while expecting atom at byte %d in line "%s"' %(i, u(line)))
    return line[x:i], i

def parse_string(line, i):
    end = len(line)
    if i == end or line[i] != 0x22:
        raise Exception('Did not find expected string at byte %d in line %s' %(i, u(line)))
    i += 1
    s = []
    while i < end:
        if line[i] == 0x22:
            return bytes(s), i+1
        if line[i] == 0x5c:
            if end - i < 2 or (line[i+1] == 'x' and end - i < 4):
                raise Exception('Failed to parse escape sequence at byte %d in line %s' %(i, u(line)))
            m = { 0x22: 0x22, 0x5c: 0x5c, 0x6e: 0x0a, 0x72: 0x0d, 0x74: 0x09 }
            if line[i+1] in m:
                s.append(m[line[i+1]])
                i += 2
            elif line[i+1] == 0x78:
                hi = hexconvert(line[i+2])
                lo = hexconvert(line[i+3])
                if hi is None or lo is None:
                    raise Exception('Failed to convert hex sequence at byte %d in line %s' %(i, u(line)))
                s.append(hi*16 + lo)
                i += 4
            else:
                raise Exception('Failed to convert escape sequence at byte %d in line %s' %(i, u(line)))
        elif line[i] >= 0x20 and line[i] != 0x7f:
            s.append(line[i])
            i += 1
        else:
            raise Exception('Failed to parse string literal at byte %d in line %s' %(i, u(line)))

def parse_space(line, i):
    end = len(line)
    if i == end:
        raise Exception('Expected whitespace but found EOL in line %s' %(u(line),))
    if line[i] != 0x20:
        raise Exception('Expected whitespace in line %s at position %d' %(u(line), i))
    return i+1

def parse_cells(line, i, cols):
    end = len(line)
    cs = []
    for col in cols:
        i = parse_space(line, i)
        if col.syntaxtype == SYNTAX_ATOM:
            s, i = parse_atom(line, i)
        else:
            s, i = parse_string(line, i)
        cs.append(col.decode(s))
    if i != end:
        raise Exception('Expected EOL at byte %d in line %s' %(i, u(line)))
    return tuple(cs)

def parse_row(line, cols):
    end = len(line)
    i = 0
    table, i = parse_atom(line, 0)
    cols = cols.get(table)
    if cols is None:
        raise Exception('No such table: "%s" while parsing line: %s' %(u(table), u(line)))
    return table, parse_cells(line, i, cols)

def format_atom(token):
    return token

def format_string(token):
    x = token
    # XXX some escaping missing
    x = x.replace(b'\\',b'\\\\')
    x = x.replace(b'"',b'\\"')
    x = b'"' + x + b'"'
    return x

def format_row(table, row, cols):
    x = [table]
    for val, col in zip(row, cols):
        token = col.encode(val)
        if col.syntaxtype == SYNTAX_ATOM:
            x.append(format_atom(token))
        else:
            x.append(format_string(token))
    return b' '.join(x) + b'\n'

def split_schema(lines):
    lines = L1(iter(lines))
    schlines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not line.startswith(b'%'):
            lines.unget(line)
            break
        schlines.append(line.lstrip(b'% '))
    return schlines, lines

def parse_db(binary_io, schema=None, datatypes=None):
    lines = binary_io.readlines()
    if schema is None:
        schemalines, dblines = split_schema(lines)
        schema = parse_schema(schemalines, datatypes)
    else:
        dblines = lines
    db = Database(schema)
    for line in dblines:
        line = line.strip()
        if line:
            table, row = parse_row(line, schema.cols)
            db.add_row(table, row)
    return db
