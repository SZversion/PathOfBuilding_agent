# External Search

`search_external` runs on the local Python Bridge and makes read-only HTTPS requests. It never opens a browser or follows a model-provided URL.

## Arguments

- `query` (required): 1–200 characters after trimming
- `source` (optional): `both` (default), `poewiki`, or `poedb`
- `limit` (optional): 1–3 results per selected source (default 3)

## Providers

- **PoE Wiki:** `https://www.poewiki.net/w/api.php`, using MediaWiki `action=query&list=search` to find pages and `action=parse&prop=text` to fetch each selected page's rendered body.
- **PoEDB:** its public English autocomplete index, which the website UI loads from the PoEDB CDN. The Bridge discovers the current hashed index through the site's public header script, caches it in memory for six hours, ranks title matches locally, then fetches each matching page directly over HTTPS and extracts `#markContent`.

The Bridge allows HTTPS requests only to `www.poewiki.net`, `poedb.tw`, and `cdn.poedb.tw`. Responses are limited to 4 MiB and requests time out after 10 seconds. Redirects to other hosts are rejected.

## Result and evidence

The common envelope's `facts.results` entries contain `source`, `title`, `url`, `content`, `contentTruncated`, `contentStatus`, `retrievedAt`, `evidenceType: temporary_evidence`, and an `evidenceId`. `content` is extracted from the page body and capped at 12,000 characters per result; `contentTruncated` reports whether the cap was reached. The envelope's `sources` contains the cited URLs, and `evidenceGraph` links each result to its source. `facts.failedSources` records providers that failed; a successful result from the other provider is retained with `status: partial`. A successful lookup uses `status: calculated`; no results uses `unavailable`.

External results are temporary references for the current answer. The tool does not save them to the local knowledge base, and they cannot replace PoB-calculated values or become canonical rules without separate review.
