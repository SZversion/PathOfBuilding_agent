import json
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from agent.cli import run_cli


@pytest.mark.parametrize("changed", [False, True])
def test_cli_live_snapshot_revision_checks_calculated_state(tmp_path, capsys, monkeypatch, changed):
    from agent.orchestration.runtime import SnapshotSync

    build = tmp_path / "live.xml"
    build.write_text("<Build/>", encoding="utf-8")
    calls = []

    class Client:
        def __init__(self, **kwargs): self.reads = 0
        def start(self): return self
        def list_tools(self): return None
        def read_resource(self):
            self.reads += 1
            return {"status": "ok", "snapshotRevision": None, "facts": {
                "schemaVersion": 1, "snapshotRevision": "unknown", "characterLevel": 98,
                "outputs": {"TotalDPS": 200 if changed and self.reads > 1 else 100},
                "skills": [{"name": "Arc", "output": {"TotalDPS": 100}}],
            }}
        def call_tool(self, name, arguments):
            calls.append(name)
            return {"status": "ok", "facts": {"TotalDPS": 100}, "sources": ["PoB"]}
        def close(self): pass

    class Provider:
        def __init__(self): self.calls = 0
        def chat(self, messages):
            self.calls += 1
            if self.calls > 1: return "PoB DPS: 100"
            revision = SnapshotSync().prepare(Client().read_resource())["snapshotRevision"]
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer",
                "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats",
                "arguments": {}, "expectedSnapshotRevision": revision}]})

    monkeypatch.setattr("agent.cli.McpToolClient", Client)
    run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "DPS?", "--json"],
            provider_factory=lambda args: Provider())
    output = json.loads(capsys.readouterr().out)
    if changed:
        assert calls == []
        assert output["execution"]["steps"][0]["error"]["code"] == "SNAPSHOT_REVISION_CONFLICT"
    else:
        assert calls == ["get_character_stats"]
        assert output["status"] == "ok"


def test_live_snapshot_projection_preserves_pob_values():
    from agent.orchestration.runtime import SnapshotSync, snapshot_revision
    raw = {"status": "ok", "snapshotRevision": None, "facts": {
        "schemaVersion": 1, "snapshotRevision": "unknown", "outputs": {"TotalDPS": 100},
        "skills": [{"name": "Arc", "output": {"TotalDPS": 100}}],
    }}
    sync = SnapshotSync().prepare(raw)
    assert sync["snapshot"]["calculatedSnapshot"]["outputs"]["TotalDPS"] == 100
    assert sync["snapshot"]["calculatedSnapshot"]["skills"][0]["name"] == "Arc"
    assert snapshot_revision(raw) == sync["snapshotRevision"]


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def chat(self, messages):
        self.calls += 1
        if self.calls == 1:
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})
        return "정상 답변"


class FakeBridge:
    def __init__(self, build):
        self.calls = []

    def call(self, build, tool, arguments):
        self.calls.append(tool)
        return {"life": 100, "snapshotRevision": "r1"}


def test_cli_once_json_and_cache_restore(tmp_path, capsys):
    build = tmp_path / "sample.xml"
    build.write_text("<Build/>", encoding="utf-8")
    provider = FakeProvider()
    result = run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "life?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: provider)
    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"
    assert list((tmp_path / "cache").glob("*/snapshot.json"))


def test_cli_rejects_local_model_without_explicit_flag(tmp_path, capsys):
    build = tmp_path / "sample.xml"
    build.write_text("<Build/>", encoding="utf-8")
    result = run_cli(["--build", str(build), "--model", "qwen3:8b", "--once", "life?", "--json"], bridge_factory=FakeBridge)
    assert result == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "INPUT_INVALID"


def test_cli_json_error_includes_confirmation_type(tmp_path, capsys):
    build = tmp_path / "ask-json.xml"
    build.write_text("<Build/>", encoding="utf-8")
    class Asking:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "unknown", "operation": "answer", "steps": [], "ambiguities": ["skill"]})
    assert run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "which?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: Asking()) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error"]["details"]["confirmation_type"] == "ask"


def test_cli_rejects_missing_or_non_xml_build(tmp_path, capsys):
    result = run_cli(["--build", str(tmp_path / "missing.xml"), "--once", "life?", "--json"])
    assert result == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "INPUT_INVALID"


def test_cli_ask_user_is_structured_and_cached(tmp_path, capsys):
    build = tmp_path / "sample.xml"
    build.write_text("<Build/>", encoding="utf-8")

    class AskingProvider:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "unknown", "operation": "answer", "steps": [], "ambiguities": ["skill"]})

    result = run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "which skill?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: AskingProvider())
    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error"]["code"] == "AMBIGUOUS_ALIAS"


def test_cli_persists_bridge_revision_and_resumes_pending(tmp_path, capsys):
    build = tmp_path / "sample.xml"
    cache_root = tmp_path / "cache"
    build.write_text("<Build/>", encoding="utf-8")
    class Asking:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "unknown", "operation": "answer", "steps": [], "ambiguities": ["skill"]})
    assert run_cli(["--build", str(build), "--cache-root", str(cache_root), "--once", "which?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: Asking()) == 1
    capsys.readouterr()
    saved = json.loads(next(cache_root.glob("*/snapshot.json")).read_text(encoding="utf-8"))
    assert saved["payload"]["snapshotRevision"] == "r1"
    class Answering:
        def __init__(self): self.calls = 0
        def chat(self, messages):
            self.calls += 1
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]}) if self.calls == 1 else "resolved"
    assert run_cli(["--build", str(build), "--cache-root", str(cache_root), "--expected-snapshot-revision", "r1", "--clarification-answer", "arc", "--once", "which?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: Answering()) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_cli_streams_text_tokens_and_json_remains_one_envelope(tmp_path, capsys):
    build = tmp_path / "stream.xml"
    build.write_text("<Build/>", encoding="utf-8")
    class Streaming:
        def __init__(self): self.calls = 0
        def chat(self, messages):
            self.calls += 1
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})
        def stream_chat(self, messages):
            yield "토큰"
            yield "순서"
    provider = Streaming()
    assert run_cli(["--build", str(build), "--cache-root", str(tmp_path / "text-cache"), "--once", "life?"], bridge_factory=FakeBridge, provider_factory=lambda args: provider) == 0
    assert capsys.readouterr().out == "토큰순서\n"
    provider = Streaming()
    assert run_cli(["--build", str(build), "--cache-root", str(tmp_path / "json-cache"), "--once", "life?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: provider) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["answer"] == "토큰순서"
    assert output.count("\n") == 1


def test_cli_default_stream_ask_user_is_natural_text(tmp_path, capsys):
    build = tmp_path / "ask.xml"
    build.write_text("<Build/>", encoding="utf-8")
    class Asking:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "unknown", "operation": "answer", "steps": [], "ambiguities": ["skill"]})
    assert run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "which?"], bridge_factory=FakeBridge, provider_factory=lambda args: Asking()) == 1
    output = capsys.readouterr().out
    assert output.startswith("추가 정보가 필요합니다")
    assert "AMBIGUOUS_ALIAS" not in output


def test_cli_initial_error_is_not_json_in_text_mode(tmp_path, capsys):
    assert run_cli(["--build", str(tmp_path / "missing.xml"), "--once", "life?"]) == 1
    output = capsys.readouterr().out
    assert not output.lstrip().startswith("{")


def test_cli_streams_final_answer_tokens_in_text_mode(tmp_path, capsys):
    build = tmp_path / "stream sample.xml"
    build.write_text("<Build/>", encoding="utf-8")

    class StreamingProvider:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})

        def stream_chat(self, messages):
            yield "토큰"
            yield " 단위"

    result = run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "life?"], bridge_factory=FakeBridge, provider_factory=lambda args: StreamingProvider())
    assert result == 0
    assert capsys.readouterr().out == "토큰 단위\n"


def test_cli_json_buffers_stream_without_stdout_tokens(tmp_path, capsys):
    build = tmp_path / "stream sample.xml"
    build.write_text("<Build/>", encoding="utf-8")

    class StreamingProvider:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})

        def stream_chat(self, messages):
            yield "토큰"
            yield " 단위"

    result = run_cli(["--build", str(build), "--cache-root", str(tmp_path / "cache"), "--once", "life?", "--json"], bridge_factory=FakeBridge, provider_factory=lambda args: StreamingProvider())
    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["answer"] == "토큰 단위"
