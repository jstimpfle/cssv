"""Module wsl.integrity: WSL Database Integrity"""

import wsl.schema

def check_integrity(schema, tuples_of_relation):
    """Check the integrity of a database.

    Args:
        schema: A *wsl.Schema* object
        tuples_of_relation: A dict which maps each relation name in
            *schema.relations* to a list of database tuples.

    Returns:
        A list of all the problems that were found. (If no problems were found
        an empty list is returned).
    """

    def key_from_tup(tup, ix):
        return tuple(tup[i] for i in ix)

    class RelationData:
        def __init__(self):
            self.keys = []  # list of (name, indices, index-set)
            self.refs = []  # list of (indices, index-set)

    data_of = dict()
    for relation in schema.relations:
        data_of[relation] = RelationData()
        data_of[relation].keys.append((b'NODUPLICATEROWS', list(range(len(schema.domains_of_relation[relation]))), set()))
    for name in schema.keys:
        rel, ix = schema.tuple_of_key[name]
        data_of[rel].keys.append((name, ix, set()))
    for name in schema.references:
        rel1, ix1, rel2, ix2 = schema.tuple_of_reference[name]
        x = set()
        data_of[rel1].refs.append((name, ix1, x))
        data_of[rel2].keys.append((name, ix2, x))

    problems = []
    for relation in schema.relations:
        data = data_of[relation]
        for tup in tuples_of_relation[relation]:
            for name, ix, x in data.keys:
                key = key_from_tup(tup, ix)
                if key in x:
                    problems.append('Unique key constraint violated: %s %s' %(relation, tup))
                x.add(key)
    for relation in schema.relations:
        data = data_of[relation]
        for tup in tuples_of_relation[relation]:
            for name, ix, x in data.refs:
                key = key_from_tup(tup, ix)
                if key not in x:
                    problems.append('Row (%s %s) violates referential integrity: %s' %(relation, tup, name))
    return problems
