import pathlib
import sys
import json
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.search.external_search import ExternalSearch
from agent.orchestration.agent_loop import ALLOWED_TOOLS, validate_plan
from agent.orchestration.runtime import execute_plan
from agent.pob.bridge import make_pob_handlers


class FakeResponse:
    def __init__(self, body, url="https://www.poewiki.net/w/api.php"):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]

    def geturl(self):
        return self.url


def test_poewiki_search_uses_mediawiki_api_and_returns_cited_temporary_evidence(monkeypatch):
    seen = []

    import agent.search.external_search as module

    def fake_urlopen(request, timeout):
        seen.append((request.full_url, timeout))
        params = parse_qs(urlparse(request.full_url).query)
        if params.get("action") == ["parse"]:
            body = {"parse": {"title": "Arc", "text": {"*": '<div class="mw-parser-output"><h2>Mechanics</h2><p>Chains <b>nearby enemies</b>.</p><script>hidden text</script><div class="navbox">navigation text</div></div>'}}}
        else:
            body = {"query": {"search": [{"title": "Arc", "timestamp": "2026-10-01T12:00:00Z"}]}}
        return FakeResponse(json.dumps(body), request.full_url)

    monkeypatch.setattr(module, "_urlopen", fake_urlopen)

    result = ExternalSearch().search("Arc", source="poewiki")

    assert len(result["facts"]["results"]) == 1
    item = result["facts"]["results"][0]
    assert item["title"] == "Arc"
    assert item["content"] == "Mechanics\nChains nearby enemies."
    assert "hidden text" not in item["content"]
    assert "navigation text" not in item["content"]
    assert item["url"] == "https://www.poewiki.net/wiki/Arc"
    assert item["source"] == "poewiki"
    assert result["sources"][0] == item["url"]
    assert result["evidenceGraph"]["sourceEdges"][0]["type"] == "supported_by"
    assert result["status"] == "calculated"
    assert "list=search" in seen[0][0]


def test_poedb_search_ranks_cached_autocomplete_index(monkeypatch):
    import agent.search.external_search as module

    payloads = {
        "https://poedb.tw/us/": '<script src="https://cdn.poedb.tw/js/poedb_header.hash.js"></script>',
        "https://cdn.poedb.tw/js/poedb_header.hash.js": "'autocomplete_us.json': 'autocomplete_us.hash.json'",
        "https://cdn.poedb.tw/json/autocomplete_us.hash.json": '[{"label":"Arc","value":"Arc","desc":"Skill Gems"},{"label":"Arcane Surge","value":"Arcane_Surge","desc":"Support Gems"}]',
        "https://poedb.tw/us/Arc": '<html><nav>navigation text</nav><div class="page-content theme-showcase container" role="main"><div class="related">outside content</div><div id="markContent"><h1>Arc</h1><p>Deals <b>lightning damage</b>.</p><script>hidden text</script></div><div>after content</div></div></html>',
        "https://poedb.tw/us/Arcane_Surge": '<html><div role="main"><h1>Arcane Surge</h1><p>Grants spell damage.</p></div></html>',
    }
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        return FakeResponse(payloads[request.full_url], request.full_url)

    monkeypatch.setattr(module, "_urlopen", fake_urlopen)
    search = ExternalSearch()

    result = search.search("Arc", source="poedb", limit=1)
    again = search.search("Arcane", source="poedb")

    assert result["facts"]["results"][0]["title"] == "Arc"
    assert result["facts"]["results"][0]["url"] == "https://poedb.tw/us/Arc"
    assert result["facts"]["results"][0]["content"] == "Arc\nDeals lightning damage."
    assert "navigation text" not in result["facts"]["results"][0]["content"]
    assert "hidden text" not in result["facts"]["results"][0]["content"]
    assert "outside content" not in result["facts"]["results"][0]["content"]
    assert "after content" not in result["facts"]["results"][0]["content"]
    assert again["facts"]["results"][0]["title"] == "Arcane Surge"
    assert again["facts"]["results"][0]["content"] == "Arcane Surge\nGrants spell damage."
    assert len(seen) == 5


def test_page_content_is_truncated_at_the_declared_limit():
    from agent.search.external_search import _bounded_content

    content, truncated = _bounded_content("x" * 12025)

    assert len(content) == 12000
    assert truncated is True


def test_external_search_validates_query_source_and_limit():
    search = ExternalSearch()
    with pytest.raises(ValueError):
        search.search("  ")
    with pytest.raises(ValueError):
        search.search("Arc", source="all-web")
    with pytest.raises(ValueError):
        search.search("Arc", limit=0)
    with pytest.raises(ValueError):
        search.search("Arc", limit=4)
    with pytest.raises(ValueError):
        search.search("Arc", source=[])


def test_external_redirects_cannot_leave_approved_hosts():
    from urllib.error import HTTPError
    from urllib.request import Request
    import agent.search.external_search as module

    handler = module._ApprovedRedirectHandler()
    with pytest.raises(HTTPError):
        handler.redirect_request(Request("https://poedb.tw/us/"), None, 302, "Found", {}, "https://example.com/collect")


def test_both_sources_keep_successful_results_when_one_source_fails(monkeypatch):
    import agent.search.external_search as module

    class PartialSearch(ExternalSearch):
        def _search_poewiki(self, query, limit):
            raise OSError("offline")

        def _search_poedb(self, query, limit):
            return [{"source": "poedb", "title": "Arc", "url": "https://poedb.tw/us/Arc", "snippet": "Skill Gems"}]

    result = PartialSearch().search("Arc", source="both")

    assert result["status"] == "partial"
    assert [item["source"] for item in result["facts"]["results"]] == ["poedb"]
    assert result["facts"]["failedSources"] == ["poewiki"]
    assert result["snapshotRevision"] == "not_applicable"
    assert "conditions" in result and "operator_message" in result


def test_external_search_is_registered_and_executable_as_a_public_tool():
    assert "search_external" in ALLOWED_TOOLS
    planned = validate_plan({"intent": "search", "steps": [{
        "tool": "search_external", "arguments": {"query": "Arc", "source": "both", "limit": 3}
    }]})
    calls = []
    result = execute_plan("Arc 검색", planned, handlers={
        "search_external": lambda args: calls.append(args) or {
            "status": "ok", "facts": {"results": []}, "sources": [],
            "uncertainty": {"level": "high", "temporaryEvidence": False},
        }
    })
    assert calls == [{"query": "Arc", "source": "both", "limit": 3}]
    assert result["steps"][0]["status"] == "ok"
    assert result["tool_call_count"] == 1
    with pytest.raises(ValueError):
        validate_plan({"intent": "search", "steps": [{
            "tool": "search_external", "arguments": {"query": "Arc", "limit": 4}
        }]})


def test_pob_handler_factory_registers_external_search():
    handlers = make_pob_handlers("build.xml", luajit="luajit")
    assert callable(handlers["search_external"])
