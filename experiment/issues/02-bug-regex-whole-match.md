# Query.matches accepts a prefix although its documentation says whole string

Type: bug report. Draft, not opened or frozen.

I use Query().code.matches('[A-Z]+') to validate a code field. A document with code 'ABC123' currently matches, even though the method's documentation says the whole string has to match. Query.search already exists for substring searches.

Please have matches require the whole string, while keeping search as a substring operation. Regex flags should still work, queries with different flags should not share cached answers, and missing/non-string fields should remain nonmatches. Existing logical composition and query caching should continue to work.
