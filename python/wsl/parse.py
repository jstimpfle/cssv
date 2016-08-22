import wsl.schema
import wsl.datatype

def u(bin):
    try:
        return bin.decode('utf-8')
    except UnicodeDecodeError:
        s = bin.decode('utf-8', 'backslashreplace')
        raise Exception('Not valid UTF-8: "%s"' % (s,))

def uj(bins):
    return ' '.join(u(bin) for bin in bins)

def hexconvert(c):
    x = ord(c)
    if 48 <= x < 58:
        return x - 48
    if 97 <= x < 103:
        return 10 + x - 97
    return None

class Ahead:
    def __init__(self, iter):
        assert hasattr(iter, '__next__')
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

def split_header(ahead):
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
    if i == end or line[i] != 0x20:
        raise Exception('Expected space character in line %s at position %d' %(u(line), i))
    return i+1

def parse_values(line, i, datatypes):
    end = len(line)
    vs = []
    for dt in datatypes:
        i = parse_space(line, i)
        if dt.syntaxtype == wsl.datatype.SYNTAX_ATOM:
            s, i = parse_atom(line, i)
        elif dt.syntaxtype == wsl.datatype.SYNTAX_STRING:
            s, i = parse_string(line, i)
        else:
            assert False
        val = dt.decode(s)
        vs.append(val)
    if i != end:
        raise Exception('Expected EOL at byte %d in line %s' %(i, u(line)))
    return tuple(vs)

def parse_row(line, datatypes_of_relation):
    end = len(line)
    relation, i = parse_atom(line, 0)
    datatypes = datatypes_of_relation.get(relation)
    if datatypes is None:
        raise Exception('No such table: "%s" while parsing line: %s' %(u(relation), u(line)))
    return relation, parse_values(line, i, datatypes)

def parse_db(lines, schemastring, datatype_parsers):
    lookahead = Ahead(lines)

    if schemastring is None:
        schemastring = split_header(lookahead)
    schema = wsl.schema.parse_schema(schemastring, datatype_parsers)

    datatypes_of_relation = wsl.schema.make_datatypes_of_relation(schema)
    tuples_of_relation = dict()
    for relation in schema.relations:
        tuples_of_relation[relation] = []
    for line in lookahead:
        line = line.strip()
        if line:
            r, tup = parse_row(line, datatypes_of_relation)
            tuples_of_relation[r].append(tup)

    return schema, tuples_of_relation
