# Add a pop operation that returns the removed document

Type: small feature request. Draft, not opened or frozen.

My work queue currently calls get(doc_id=...) and then remove(doc_ids=...) just to retrieve a document and take it out of a table. Could Table expose pop(doc_id), returning the removed Document with its doc_id and raising KeyError when that ID is missing?

Please leave other tables and documents alone, invalidate the affected table's query-result cache as normal, and use the configured document_class rather than always constructing the built-in Document. I also want the usual default-table delegation so db.pop(id) works. This is a convenience operation over the current whole-state storage interface; I am not asking for cross-process transactions.
