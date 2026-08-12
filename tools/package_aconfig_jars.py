#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import zipfile

AOSP_JAVAC = Path(
    "/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/libs/systemui/"
    "aconfig/com_android_systemui_shared_flags_lib/android_common/javac/"
    "com_android_systemui_shared_flags_lib.jar"
)
CONFIGS = {
    "systemui-shared-flags": (AOSP_JAVAC, Path("libs/systemui-shared-flags.jar")),
}


def copy_jar(source: Path, destination: Path) -> None:
    source = Path(source)
    destination = Path(destination)
    if "turbine" in source.parts:
        raise ValueError(f"runtime JAR must not come from turbine: {source}")
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise FileNotFoundError(f"missing or invalid AOSP JAR: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package concrete AOSP aconfig JARs")
    parser.add_argument("artifact", choices=sorted(CONFIGS))
    args = parser.parse_args()
    source, destination = CONFIGS[args.artifact]
    copy_jar(source, destination)
    print(f"{args.artifact}: {source} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
