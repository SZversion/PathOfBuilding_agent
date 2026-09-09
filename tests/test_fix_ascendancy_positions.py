import filecmp
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import fix_ascendancy_positions


def test_fix_one() -> None:
    fixture = pathlib.Path(__file__).parent / "fixtures" / "ascendancy"
    raw = fixture / "sample.json"
    with tempfile.TemporaryDirectory() as td:
        new = pathlib.Path(td, raw.name)
        shutil.copy(raw, td)
        fix_ascendancy_positions.fix_ascendancy_positions(new)
        result = json.loads(new.read_text())
        assert "nodes" in result and "groups" in result


def test_fix_all() -> None:
    fixture = pathlib.Path(__file__).parent / "fixtures" / "ascendancy"
    raw = fixture / "sample.json"
    with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory(
        dir=outer
    ) as inner:
        root = pathlib.Path(outer)
        new = pathlib.Path(inner, raw.name)
        shutil.copy(raw, inner)
        fix_ascendancy_positions.main(root)
        result = json.loads(new.read_text())
        assert "nodes" in result and "groups" in result
