# Removing the same document ID twice raises an unexpected KeyError

Type: bug report. Draft, not opened or frozen.

I collect document IDs from several search results and pass the combined list to remove(doc_ids=...). If two searches found the same document, remove raises KeyError even though missing IDs are supposed to be skipped. For example, insert two documents and call remove(doc_ids=[first_id, first_id, 99999]).

Please make repeated IDs safe, remove each existing document only once, and return the unique IDs actually removed in their first-requested order. Keep the current behavior for missing IDs. Other documents and other tables should remain intact, and a cached search should reflect the successful removal. I use both MemoryStorage and JSONStorage; please preserve their existing storage contract.
