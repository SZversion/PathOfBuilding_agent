import hashlib
import xml.etree.ElementTree as ET
import update_manifest


def test_generated_manifest_uses_agent_fork_main_and_tracks_agent_assets(tmp_path, monkeypatch):
    (tmp_path / "manifest.xml").write_text(
        "<PoBVersion><Version number='2.67.2'/></PoBVersion>", encoding="utf-8"
    )
    (tmp_path / "manifest.cfg").write_text(
        """[default]
path = .
include-files = release-notes.txt

[runtime]
path = runtime

[program]
path = src
""",
        encoding="utf-8",
    )
    files = {
        "release-notes.txt": b"release notes\n",
        "runtime/SimpleGraphic.dll": b"renderer-binary\x00",
        "runtime/SimpleGraphic/Fonts/NotoSansKR-Regular.ttf": b"font-binary\x00",
        "src/Modules/AgentBridge.lua": b"return {}\n",
    }
    for relative_path, content in files.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    monkeypatch.chdir(tmp_path)
    update_manifest.create_manifest()

    root = ET.parse(tmp_path / "manifest-updated.xml").getroot()
    version = root.find("Version")
    assert version is not None
    assert version.attrib == {"number": "2.67.2", "branch": "main", "platform": "win32"}
    sources = {source.attrib["part"]: source.attrib["url"] for source in root.findall("Source")}
    assert sources["default"] == "https://raw.githubusercontent.com/SZversion/PathOfBuilding_agent/{branch}/"
    assert sources["program"].endswith("/{branch}/src/")
    assert sources["runtime"].endswith("/{branch}/runtime/")

    entries = {entry.attrib["name"]: entry.attrib for entry in root.findall("File")}
    for relative_path, content in files.items():
        if relative_path == "release-notes.txt":
            name, part = relative_path, "default"
        elif relative_path.startswith("runtime/"):
            name, part = relative_path.removeprefix("runtime/"), "runtime"
        else:
            name, part = relative_path.removeprefix("src/"), "program"
        assert entries[name]["part"] == part
        hash_content = content
        if b"\0" not in content:
            hash_content = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            hash_content = hash_content.replace(b"\n", b"\r\n")
        assert entries[name]["sha1"] == hashlib.sha1(hash_content).hexdigest()
