"""Read-only HTTP search for PoE Wiki and PoEDB references."""

from html.parser import HTMLParser
import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote, urlencode, urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


POEWIKI_API = "https://www.poewiki.net/w/api.php"
POEDB_HOME = "https://poedb.tw/us/"
POEDB_CDN = "https://cdn.poedb.tw"
REQUEST_TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_QUERY_LENGTH = 200
MAX_RESULTS = 3
MAX_CONTENT_CHARS = 12000
POEDB_CACHE_SECONDS = 6 * 60 * 60
USER_AGENT = "PathOfBuildingAgent/1.0 (read-only PoE reference search)"
APPROVED_HOSTS = {"www.poewiki.net", "poedb.tw", "cdn.poedb.tw"}


class _ApprovedRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        target = urlparse(new_url)
        if target.scheme != "https" or target.hostname not in APPROVED_HOSTS:
            raise HTTPError(new_url, code, "redirect outside approved search sites", headers, response)
        return super().redirect_request(request, response, code, message, headers, new_url)


def _urlopen(request, timeout):
    return build_opener(_ApprovedRedirectHandler()).open(request, timeout=timeout)


class _ArticleTextExtractor(HTMLParser):
    """Extract readable text from the page's article/main content region."""

    BLOCK_TAGS = {"article", "br", "dd", "div", "dl", "dt", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ol", "p", "section", "table", "td", "th", "tr", "ul"}
    SKIP_TAGS = {"button", "footer", "header", "nav", "noscript", "script", "style", "svg"}
    SKIP_CLASSES = {"mw-editsection", "navbox", "reflist", "references", "toc"}

    def __init__(self, provider, target_id=None):
        super().__init__()
        self.provider = provider
        self.target_id = target_id
        self.depth = 0
        self.root_depth = None
        self.skip_stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if self.skip_stack:
            if tag in self.SKIP_TAGS:
                self.skip_stack.append(tag)
            return
        if tag in self.SKIP_TAGS or attributes.get("role") == "navigation" or classes & self.SKIP_CLASSES:
            self.skip_stack.append(tag)
            return
        if self.root_depth is None:
            is_root = (self.provider == "poewiki" and "mw-parser-output" in classes) or (
                self.provider == "poedb" and (
                    attributes.get("id") == self.target_id if self.target_id else attributes.get("role") == "main"
                )
            )
            if is_root:
                self.root_depth = self.depth
        if self.root_depth is not None and tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        elif self.root_depth is not None:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            self.depth = max(0, self.depth - 1)
            return
        if self.root_depth is not None and tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        elif self.root_depth is not None:
            self.parts.append(" ")
        if self.root_depth == self.depth:
            self.root_depth = None
        self.depth = max(0, self.depth - 1)

    def handle_data(self, data):
        if self.root_depth is not None and not self.skip_stack:
            self.parts.append(data)


def _article_text(value, provider, target_id=None):
    parser = _ArticleTextExtractor(provider, target_id=target_id)
    parser.feed(value or "")
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    lines = [re.sub(r"\s+([.,!?;:])", r"\1", line) for line in lines if line.strip()]
    return "\n".join(lines)


def _bounded_content(value):
    if len(value) <= MAX_CONTENT_CHARS:
        return value, False
    return value[:MAX_CONTENT_CHARS].rstrip(), True


def _read_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in APPROVED_HOSTS:
        raise ValueError("external search URL is outside the approved sites")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.1"})
    with _urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in APPROVED_HOSTS:
            raise ValueError("external search redirected outside the approved sites")
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("external search response exceeded the size limit")
    return body.decode("utf-8", errors="replace")


def _tokens(value):
    return set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE))


class ExternalSearch:
    """Queries PoE Wiki's MediaWiki API and PoEDB's public autocomplete index."""

    def __init__(self):
        self._poedb_entries = None
        self._poedb_loaded_at = 0
        self._cache_lock = threading.Lock()

    def search(self, query, source="both", limit=3):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        query = query.strip()
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError("query exceeds the 200-character limit")
        if not isinstance(source, str) or source not in {"poedb", "poewiki", "both"}:
            raise ValueError("source must be poedb, poewiki, or both")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
            raise ValueError("limit must be an integer from 1 to 3")

        providers = []
        if source in {"poewiki", "both"}:
            providers.append(("poewiki", self._search_poewiki))
        if source in {"poedb", "both"}:
            providers.append(("poedb", self._search_poedb))

        results, failed = [], []
        for name, provider in providers:
            try:
                provider_results = provider(query, limit)
                if isinstance(provider_results, tuple):
                    source_results, provider_failed = provider_results
                else:
                    source_results, provider_failed = provider_results, False
                results.extend(source_results)
                if provider_failed:
                    failed.append(name)
            except (OSError, TimeoutError, ValueError):
                failed.append(name)

        retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        nodes, source_edges, sources = [], [], []
        for index, item in enumerate(results, 1):
            item["retrievedAt"] = retrieved_at
            item["evidenceType"] = "temporary_evidence"
            result_id = "external-result:%d" % index
            source_id = "external-source:%d" % index
            item["evidenceId"] = result_id
            nodes.extend((
                {"id": result_id, "type": "search_result", "title": item["title"], "evidenceType": "temporary_evidence"},
                {"id": source_id, "type": "external_source", "source": item["source"], "url": item["url"], "retrievedAt": retrieved_at},
            ))
            source_edges.append({"from": result_id, "to": source_id, "type": "supported_by"})
            if item["url"] not in sources:
                sources.append(item["url"])

        if not failed and results:
            status = "calculated"
        elif results:
            status = "partial"
        else:
            status = "unavailable"
        uncertainty = {"level": "medium" if results else "high", "temporaryEvidence": bool(results), "reasons": [], "missingEvidence": []}
        if failed:
            uncertainty["reasons"].append("one_or_more_search_sources_failed")
        if not results:
            uncertainty["reasons"].append("no_external_search_results")
        return {
            "status": status,
            "snapshotRevision": "not_applicable",
            "side_effect": "none",
            "operator_message": None,
            "facts": {"query": query, "results": results[:limit * len(providers)], "failedSources": failed},
            "conditions": [],
            "trace": [],
            "sources": sources,
            "version": {"gamePatch": None, "pobVersion": None, "dataRevision": None},
            "evidenceGraph": {"nodes": nodes, "stages": [], "sourceEdges": source_edges},
            "uncertainty": uncertainty,
        }

    def _search_poewiki(self, query, limit):
        params = urlencode({
            "action": "query", "list": "search", "srsearch": query,
            "srprop": "timestamp", "srlimit": min(limit, MAX_RESULTS),
            "format": "json", "utf8": "1",
        })
        payload = json.loads(_read_url(POEWIKI_API + "?" + params))
        rows = payload.get("query", {}).get("search") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("PoE Wiki returned an invalid search response")
        results, failed = [], False
        for row in rows[:limit]:
            title = row.get("title")
            if not isinstance(title, str) or not title:
                continue
            page = quote(title.replace(" ", "_"), safe="()_,-")
            result = {
                "source": "poewiki",
                "title": title,
                "url": "https://www.poewiki.net/wiki/" + page,
                "lastModified": row.get("timestamp"),
            }
            try:
                params = urlencode({"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": "1"})
                payload = json.loads(_read_url(POEWIKI_API + "?" + params))
                raw_html = payload.get("parse", {}).get("text", {}).get("*")
                if not isinstance(raw_html, str):
                    raise ValueError("PoE Wiki returned no page content")
                content = _article_text(raw_html, "poewiki")
                if not content:
                    raise ValueError("PoE Wiki page content was empty")
                result["content"], result["contentTruncated"] = _bounded_content(content)
                result["contentStatus"] = "available"
            except (OSError, TimeoutError, ValueError):
                result.update({"content": "", "contentTruncated": False, "contentStatus": "unavailable"})
                failed = True
            results.append(result)
        return results, failed

    def _load_poedb_entries(self):
        with self._cache_lock:
            if self._poedb_entries is not None and time.monotonic() - self._poedb_loaded_at < POEDB_CACHE_SECONDS:
                return self._poedb_entries
            homepage = _read_url(POEDB_HOME)
            script_match = re.search(r"https://cdn\.poedb\.tw/js/(poedb_header\.[A-Za-z0-9_.-]+\.js)", homepage)
            if not script_match:
                raise ValueError("PoEDB autocomplete script was not found")
            script = _read_url(POEDB_CDN + "/js/" + script_match.group(1))
            index_match = re.search(r"'autocomplete_us\.json':\s*'([^']+)'", script)
            if not index_match:
                raise ValueError("PoEDB autocomplete index was not found")
            index_name = index_match.group(1)
            if not re.fullmatch(r"autocomplete_us\.[A-Za-z0-9_.-]+\.json", index_name):
                raise ValueError("PoEDB returned an invalid autocomplete index path")
            entries = json.loads(_read_url(POEDB_CDN + "/json/" + index_name))
            if not isinstance(entries, list):
                raise ValueError("PoEDB autocomplete index is invalid")
            self._poedb_entries = entries
            self._poedb_loaded_at = time.monotonic()
            return entries

    def _search_poedb(self, query, limit):
        query_tokens = _tokens(query)
        ranked = []
        for entry in self._load_poedb_entries():
            if not isinstance(entry, dict):
                continue
            title = entry.get("label")
            path = entry.get("value")
            if not isinstance(title, str) or not isinstance(path, str):
                continue
            title = title.strip()
            normalized = title.casefold()
            needle = query.casefold()
            overlap = len(query_tokens & _tokens(title))
            if normalized == needle:
                score = 100
            elif normalized.startswith(needle):
                score = 80
            elif needle in normalized:
                score = 60
            elif overlap:
                score = 10 + overlap
            else:
                continue
            # PoEDB's index supplies relative page keys, not arbitrary URLs.
            if path.startswith(("/", "//")) or ":" in path or ".." in path:
                continue
            page = quote(path, safe="()_,-/#")
            ranked.append((score, title, {
                "source": "poedb", "title": title,
                "url": "https://poedb.tw/us/" + page,
            }))
        ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
        results, failed = [], False
        for _, _, result in ranked[:limit]:
            try:
                page_html = _read_url(result["url"])
                content = _article_text(page_html, "poedb", target_id="markContent")
                if not content:
                    content = _article_text(page_html, "poedb")
                if not content:
                    raise ValueError("PoEDB page content was empty")
                result["content"], result["contentTruncated"] = _bounded_content(content)
                result["contentStatus"] = "available"
            except (OSError, TimeoutError, ValueError):
                result.update({"content": "", "contentTruncated": False, "contentStatus": "unavailable"})
                failed = True
            results.append(result)
        return results, failed
