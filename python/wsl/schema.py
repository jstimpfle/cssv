"""Module wsl.schema: python class representing WSL database schema"""

class Schema:
    """Schema information for a WSL database.

    Attributes:
        spec: string containing the textual representation of the schema.
            This is normally the string that the schema object was parsed from.

        domains: set object, holding the identifiying names of all the domains
            used in this schema.
        relations: set object, holding the identifiying names of all the
            relations used in this schema.
        keys: set object, holding the identifying names of all the keys used
            in this schema.
        references: set object, holding the identifying names of all the
            references used in this schema.

        spec_of_domain: dict object, mapping each domain name from the
            *domains* attribute to a textual specification of that domain. It
            is guaranteed to be a single line (including the terminating
            newline character).
        spec_of_relation: dict object, mapping each relation name from the
            *relations* attribute to a textual specification of that relation.
            It is guaranteed to be a single line (including the terminating
            newline character).
        spec_of_key: dict object, mapping each key name from the *keys*
            attribute to a textual representation of that key. It is guaranteed
            to be a single line (including the terminating newline character).
        spec_of_reference: dict object, mapping each reference name from the
            *references* attribute to a textual representation of that
            reference. It is guaranteed to be a single line (including the
            terminating newline character).
        datatype_of_domain: dict object, mapping each domain name from the
            *domains* attribute to its corresponding *datatype* object.
        domains_of_relation: dict object, mapping each relation name from the
            *relations* attribute to a tuple of the names of the columns of
            that relation (in order).
        tuple_of_key: dict object, mapping each key name from the *keys*
            attribute to a tuple *(relation name, 0-based column indices)*.
            This represents the specification of the key.
        tuple_of_reference: dict object, mapping each reference name from the
            *reference* attribute to a tuple *(relation name, column indices,
            relation name, column indices)*. This represents the reference
            constraint as (compatible) keys in the local and foreign relation.

        datatypes_of_relation: dict object, mapping each relation name from the
            *relations* attribute to a tuple of the datatypes corresponding to
            the columns of that relation. This attribute is for convenience; it
            is created in the constructor from the input arguments.
        
    """
    def __init__(self, spec,
            domains, relations, keys, references,
            spec_of_relation, spec_of_domain, spec_of_key, spec_of_reference,
            datatype_of_domain, domains_of_relation, tuple_of_key, tuple_of_reference):

        for x in domains:
            assert x in spec_of_domain
            assert x in datatype_of_domain

        for xs in domains_of_relation.values():
            for x in xs:
                assert x in domains

        for x in relations:
            assert x in spec_of_relation
            assert x in domains_of_relation

        for x in keys:
            assert x in spec_of_key
            assert x in tuple_of_key

        for x in references:
            assert x in spec_of_reference
            assert x in tuple_of_reference

        self.spec = spec
        self.domains = domains
        self.relations = relations
        self.keys = keys
        self.references = references
        self.spec_of_relation = spec_of_relation
        self.spec_of_domain = spec_of_domain
        self.spec_of_key = spec_of_key
        self.spec_of_reference = spec_of_reference
        self.datatype_of_domain = datatype_of_domain
        self.domains_of_relation = domains_of_relation
        self.tuple_of_key = tuple_of_key
        self.tuple_of_reference = tuple_of_reference

        self.datatypes_of_relation = dict((rel, tuple(self.datatype_of_domain[d] for d in self.domains_of_relation[rel])) for rel in self.relations)

    def _debug_str(self):
        return """
            domains: %s
            relations: %s
            keys: %s
            references: %s
            spec_of_relation: %s
            spec_of_domain: %s
            spec_of_key: %s
            spec_of_reference: %s
            datatype_of_domain: %s
            domains_of_relation: %s
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
        self.datatype_of_domain,
        self.domains_of_relation,
        self.tuple_of_key,
        self.tuple_of_reference)
