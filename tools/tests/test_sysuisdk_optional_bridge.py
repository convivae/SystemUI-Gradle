"""The real-byte optional bridge is a placement change, never a body rewrite."""
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from test_build_sysuisdk import (
    b, _make_base_platform, _make_fake_aosp, _zip_bytes,
    _IO_UTILS, _NATIVE_ALLOC, _DDMC, BRIDGE_37,
)

EXPECTED_OPTIONAL = set(_IO_UTILS + _NATIVE_ALLOC + _DDMC)
EXPECTED_METADATA = {
    "name": "com.android.systemui.platform.bridge",
    "jar": "sysui-platform-bridge.jar",
    "manifest": False,
}


def build(tmp_path):
    base = _make_base_platform(tmp_path / "base")
    aosp = _make_fake_aosp(tmp_path / "aosp")
    output = tmp_path / "output"
    b.build_platform(aosp, base, output)
    return base, aosp, output


def test_partition_retains_all_37_original_class_bytes(tmp_path):
    _, aosp, output = build(tmp_path)
    original = b.load_bridge(b.resolve_inputs(aosp))
    android = _zip_bytes((output / "android.jar").read_bytes())
    optional = _zip_bytes((output / "optional/sysui-platform-bridge.jar").read_bytes())
    core = _zip_bytes((output / "core-for-system-modules.jar").read_bytes())
    assert set(optional) == EXPECTED_OPTIONAL
    assert not EXPECTED_OPTIONAL.intersection(android)
    for entry in BRIDGE_37:
        assert core[entry] == original[entry]
        assert (optional if entry in EXPECTED_OPTIONAL else android)[entry] == original[entry]


def test_metadata_preserves_stock_optional_library_and_files(tmp_path):
    base = _make_base_platform(tmp_path / "base")
    stock = {"name": "stock.library", "jar": "stock.jar", "manifest": True}
    (base / "optional/optional.json").write_text(json.dumps([stock]))
    (base / "optional/stock.jar").write_bytes(b"unchanged stock payload")
    aosp = _make_fake_aosp(tmp_path / "aosp")
    out = tmp_path / "output"
    b.build_platform(aosp, base, out)
    assert json.loads((out / "optional/optional.json").read_text()) == [stock, EXPECTED_METADATA]
    assert (out / "optional/stock.jar").read_bytes() == b"unchanged stock payload"
    assert json.loads((base / "optional/optional.json").read_text()) == [stock]
    marker = json.loads((out / b.MARKER_NAME).read_text())
    assert "optional/sysui-platform-bridge.jar" in marker["generated"]["inventory"]


@pytest.mark.parametrize("collision", ["name", "jar", "file"])
def test_reserved_optional_identity_or_path_is_rejected_transactionally(tmp_path, collision):
    base = _make_base_platform(tmp_path / "base")
    if collision == "file":
        (base / "optional/sysui-platform-bridge.jar").write_bytes(b"not ours")
    else:
        record = dict(EXPECTED_METADATA)
        record["jar" if collision == "name" else "name"] = "different"
        (base / "optional/optional.json").write_text(json.dumps([record]))
    aosp = _make_fake_aosp(tmp_path / "aosp")
    out = tmp_path / "output"
    with pytest.raises(b.BuildError, match="optional.*collision"):
        b.build_platform(aosp, base, out)
    assert not out.exists()
    assert not list(tmp_path.glob(".output.staging-*"))


@pytest.mark.parametrize("metadata", ["{", "{}", '["bad"]', '[{"name": "a"}]'])
def test_invalid_optional_metadata_fails_closed(tmp_path, metadata):
    base = _make_base_platform(tmp_path / "base")
    (base / "optional/optional.json").write_text(metadata)
    aosp = _make_fake_aosp(tmp_path / "aosp")
    with pytest.raises(b.BuildError, match="optional"):
        b.build_platform(aosp, base, tmp_path / "output")


def test_optional_source_collision_is_not_hidden_by_relocation(tmp_path):
    base = _make_base_platform(tmp_path / "base")
    with zipfile.ZipFile(base / "android.jar", "a") as zf:
        zf.writestr(_IO_UTILS[0], b"conflicting real bytes")
    aosp = _make_fake_aosp(tmp_path / "aosp")
    with pytest.raises(b.BuildError, match="bridge collision"):
        b.build_platform(aosp, base, tmp_path / "output")


@pytest.mark.parametrize("tamper", ["missing", "modified", "extra", "android_duplicate", "metadata"])
def test_prepublication_validator_rejects_broken_partition(tmp_path, tamper):
    base = _make_base_platform(tmp_path / "base")
    aosp = _make_fake_aosp(tmp_path / "aosp")
    original_validate = b._validate_platform

    def corrupt(staging, *args):
        optional = Path(staging) / "optional/sysui-platform-bridge.jar"
        assert optional.is_file(), "generator did not produce the optional bridge"
        entries = _zip_bytes(optional.read_bytes())
        if tamper == "missing":
            del entries[_IO_UTILS[0]]
        elif tamper == "modified":
            entries[_IO_UTILS[0]] += b"changed"
        elif tamper == "extra":
            entries["not/Approved.class"] = b"extra"
        elif tamper == "android_duplicate":
            with zipfile.ZipFile(Path(staging) / "android.jar", "a") as zf:
                zf.writestr(_IO_UTILS[0], entries[_IO_UTILS[0]])
        else:
            (Path(staging) / "optional/optional.json").write_text("[]")
        optional.write_bytes(b._write_deterministic_zip(entries))
        original_validate(staging, *args)

    with patch.object(b, "_validate_platform", side_effect=corrupt):
        with pytest.raises(b.BuildError):
            b.build_platform(aosp, base, tmp_path / "output")
    assert not (tmp_path / "output").exists()
