"""Host portability regressions; no SDK, AOSP checkout or native tools needed."""
import contextlib
import importlib
import re
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import aosp_paths
import check_source_alignment as alignment
import package_aconfig_jars as aconfig
import package_aosp_aar as aar
import package_misc_jars as misc
import package_viewcapture_motiontool_jars as viewcapture


def test_no_machine_paths_in_host_build_code():
    root = TOOLS.parent
    paths = list(root.glob("*.gradle.kts"))
    paths += list(root.glob("*/build.gradle.kts"))
    paths += list((root / "buildSrc/src").rglob("*.kt"))
    paths += list(TOOLS.glob("*.py"))
    for path in paths:
        assert not re.search(r"/(?:home|Users)/[^/\s]+/", path.read_text(encoding="utf-8")), path


def test_sdk_provider_and_python_launcher_are_shared_with_android_build():
    root = TOOLS.parent
    common = (root / "SystemUI-common/build.gradle.kts").read_text(encoding="utf-8")
    wiring = (root / "build.gradle.kts").read_text(encoding="utf-8")
    app = (root / "app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'environmentVariable("ANDROID_HOME")' not in common
    assert ".sdkComponents.sdkDirectory" in wiring
    assert 'common.dependencies.add("compileOnly"' in wiring
    assert '"uv", "run", "--project", rootDir.absolutePath, "python", patchScript' in app


def test_alignment_is_independent_of_parent_directory_name(tmp_path):
    root = tmp_path / "build" / "my checkout" / "src"
    source = root / "pkg/Foo.kt"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original")
    assert alignment.walk_source(root, {".kt"}) == {"pkg/Foo.kt": source}
    mappings = [alignment.M(["src"], "my checkout", "src")]
    assert alignment.find_tail_locations("pkg/Foo.kt", mappings, tmp_path / "build")
    assert alignment.PROJECT_ROOT == TOOLS.parent


def test_settingslib_discovery_does_not_filter_checkout_name(tmp_path):
    soong = tmp_path / "aosp-aconfig flags_lib" / "out"
    base = soong / "frameworks/base/packages/SettingsLib"
    java = base / "SettingsLib/android_common/javac/SettingsLib.jar"
    kotlin = java.parent.parent / "kotlin/SettingsLib.jar"
    for path in (java, kotlin):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"input")
    with mock.patch.object(aar, "SOONG_DIR", soong):
        assert aar._discover_settingslib_code_jars() == [java, kotlin]


@pytest.mark.parametrize("module_name,constant,relative", [
    ("package_compilelib_jars", "DEBUG_JAR", "libs/compilelib-debug.jar"),
    ("package_compilelib_jars", "RELEASE_JAR", "libs/compilelib-release.jar"),
    ("package_monet_jar", "OUTPUT_JAR", "libs/monet.jar"),
    ("package_aconfig_jars", "MERGED_FRAMEWORK_JAR", "libs/systemui-aconfig-flags.jar"),
    ("package_aosp_aar", "DEFAULT_OUTPUT", "libs/aars/animationlib.aar"),
])
def test_default_outputs_do_not_follow_working_directory(tmp_path, module_name, constant, relative):
    with contextlib.chdir(tmp_path):
        module = importlib.import_module(module_name)
        assert getattr(module, constant) == aosp_paths.PROJECT_ROOT / relative


def test_aar_default_output_is_repo_relative_but_explicit_output_is_preserved(tmp_path):
    repo, cwd = tmp_path / "checkout", tmp_path / "elsewhere"
    cwd.mkdir()
    seen = []

    def assemble(*args, **kwargs):
        output = args[4]
        seen.append(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"test archive")

    with contextlib.chdir(cwd), mock.patch.object(aar, "PROJECT_ROOT", repo), \
            mock.patch.object(aar, "assemble_aar", side_effect=assemble):
        aar.build_artifact("dynamiccolors")
        aar.build_artifact("dynamiccolors", Path("custom.aar"))
    assert seen == [repo / "libs/aars/dynamiccolors.aar", Path("custom.aar")]
    assert not (cwd / "libs").exists()


@pytest.mark.parametrize("producer", ["aconfig-merge", "aconfig-subset", "viewcapture", "misc"])
def test_zip_bytes_do_not_depend_on_host_create_system(tmp_path, producer):
    source = tmp_path / "flags.jar"
    with zipfile.ZipFile(source, "w") as archive:
        for name in sorted(aconfig.RUNTIME_CLASS_NAMES):
            archive.writestr(f"com/example/flags/{name}.class", b"test class bytes")

    def produce(output):
        if producer == "aconfig-merge":
            aconfig.merge_sources([("test", source, "com.example.flags")], output)
        elif producer == "aconfig-subset":
            with mock.patch.object(aconfig, "AGGREGATE_JAVAC_DIR", tmp_path):
                # Only framework.jarN shards are selected by the real scanner.
                shard = tmp_path / "framework.jar0"
                shard.write_bytes(source.read_bytes())
                aconfig.extract_aggregate_subset("com.example.flags", output)
        elif producer == "viewcapture":
            viewcapture.package_target((source,), output, "com/example/flags/")
        else:
            misc._extract_subset(source, output, ["com/example/flags/"])

    outputs = []
    original_zip_info = zipfile.ZipInfo
    for host_system in (0, 3):
        class HostZipInfo(original_zip_info):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.create_system = host_system

        output = tmp_path / f"output-{host_system}.jar"
        with mock.patch.object(zipfile, "ZipInfo", HostZipInfo):
            produce(output)
        outputs.append(output.read_bytes())
        with zipfile.ZipFile(output) as archive:
            assert all(info.create_system == 3 for info in archive.infolist())
    assert outputs[0] == outputs[1]
