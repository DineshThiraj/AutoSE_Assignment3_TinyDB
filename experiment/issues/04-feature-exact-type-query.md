# Filter a field by its exact Python type

Type: small feature request. Draft, not opened or frozen.

I have imported JSON-like records where the same field can be a number, boolean or string. Could Query().field.is_type(type_) produce a query that matches only values whose exact type is type_? For example is_type(int) should match 1 but not True, and is_type(bool) should match True but not 1.

Missing paths should be nonmatches. It should compose with &, | and ~ and work in the table query cache without mixing queries for different types. If the argument is not a Python type, please raise TypeError when building the query, rather than when scanning a document. Keep the normal nested field-path behavior.
