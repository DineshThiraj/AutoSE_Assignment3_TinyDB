# Let me see external updates without throwing away my open database

Type: vague request. Draft, not opened or frozen.

My app keeps a TinyDB database open with caching middleware. Sometimes another part of my program updates the stored data, but my searches still show the old version. Reopening everything is awkward. Can you make refreshing less surprising? I especially do not want pending writes to disappear.
