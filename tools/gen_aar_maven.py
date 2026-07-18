#!/usr/bin/env python3
"""
gen_aar_maven.py - 生成 AAR 并安装到本地 Maven 仓库

解决 flatDir 方式 AAR 资源无法正确合并的问题。
从 AOSP 编译产物中提取 JAR 和资源，打包成 AAR，安装到本地 Maven 仓库。

用法:
    python3 tools/gen_aar_maven.py
"""

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass


# 配置
AOSP_ROOT = Path("/home/conv/myspace/rom/jkc-A/lagvm/LINUX/android")
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
MAVEN_REPO = PROJECT_ROOT / "libs" / "maven"
GROUP_ID = "com.android.systemui"
VERSION = "1.0.0"


@dataclass
class AarConfig:
    """AAR 生成配置"""
    name: str                    # AAR 名称
    intermediate_path: str       # AOSP out 目录下的中间产物路径
    source_path: str             # 源码路径（用于获取资源）
    jar_source: Optional[str] = None  # 可选：指定 JAR 文件路径
    
    # 需要从 classes.jar 中删除的包（避免与其他 AAR 或 Maven 依赖冲突）
    packages_to_remove: List[str] = None
    
    # 需要从 res 中删除的目录/文件
    res_to_remove: List[str] = None


# AAR 配置列表
AAR_CONFIGS = [
    AarConfig(
        name="SettingsLib",
        intermediate_path="frameworks/base/packages/SettingsLib/SettingsLib",
        source_path="frameworks/base/packages/SettingsLib",
        packages_to_remove=["com/android/wifitrackerlib"],  # 由 WifiTrackerLib AAR 提供
        res_to_remove=["values-v31", "values-night-v31", "color-v31", "color-night-v31", 
                       "drawable-v31", "layout-v31"],  # Material Components 依赖
    ),
    AarConfig(
        name="iconloader",
        intermediate_path="frameworks/libs/systemui/iconloaderlib/iconloader",
        source_path="frameworks/libs/systemui/iconloaderlib",
    ),
    AarConfig(
        name="WindowManager-Shell",
        intermediate_path="frameworks/base/libs/WindowManager/Shell/WindowManager-Shell",
        source_path="frameworks/base/libs/WindowManager/Shell",
        jar_source=str(PROJECT_ROOT / "libs" / "WindowManager-Shell.jar"),  # 使用 libs 目录的 JAR
        packages_to_remove=["com/android/launcher3"],  # 与 iconloader 冲突
    ),
    AarConfig(
        name="WifiTrackerLib",
        intermediate_path="frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLib",
        source_path="frameworks/opt/net/wifi/libs/WifiTrackerLib",
        packages_to_remove=["com/android/settingslib"],  # 由 SettingsLib AAR 提供
    ),
    AarConfig(
        name="car-ui-lib",
        intermediate_path="packages/apps/Car/libs/car-ui-lib/car-ui-lib",
        source_path="packages/apps/Car/libs/car-ui-lib",
    ),
    AarConfig(
        name="car-uxr-client-lib",
        intermediate_path="packages/apps/Car/libs/car-uxr-client-lib/car-uxr-client-lib",
        source_path="packages/apps/Car/libs/car-uxr-client-lib",
        packages_to_remove=["com/android/car/ui"],  # 由 car-ui-lib AAR 提供
    ),
    AarConfig(
        name="car-assist-client-lib",
        intermediate_path="packages/apps/Car/systemlibs/car-assist-client-lib/car-assist-client-lib",
        source_path="packages/apps/Car/systemlibs/car-assist-client-lib",
    ),
    AarConfig(
        name="CarNotificationLib",
        intermediate_path="packages/apps/Car/Notification/CarNotificationLib",
        source_path="packages/apps/Car/Notification",
        packages_to_remove=["com/android/car/ui", "com/android/car/uxr", "com/android/car/assist", "com/android/car/messenger"],  # 由其他 AAR 提供
    ),
    AarConfig(
        name="car-qc-lib",
        intermediate_path="packages/apps/Car/systemlibs/car-qc-lib/car-qc-lib",
        source_path="packages/apps/Car/systemlibs/car-qc-lib",
        packages_to_remove=["com/android/car/ui"],  # 由 car-ui-lib AAR 提供
    ),
]

# 通用：需要从所有 JAR 中删除的包（与 Gradle Maven 依赖冲突）
COMMON_PACKAGES_TO_REMOVE = [
    # 第三方库
    "okio", "org/checkerframework", "com/google/common", "com/google/errorprone",
    "com/google/j2objc", "com/google/protobuf", "com/airbnb/lottie",
    "kotlinx", "kotlin", "dagger", "javax/inject", "javax/annotation",
    "org/intellij", "org/jetbrains", "android/support",
    
    # Framework 内部类（运行时由系统提供）
    "com/android/internal", "android/view/IDisplayWindowRotationController",
    "android/view/IWindow", "android/view/ISurfaceControl", "android/window",
    
    # AndroidX 标准库（通过 Gradle Maven 依赖引入）
    "androidx/annotation", "androidx/appcompat", "androidx/arch", "androidx/asynclayoutinflater",
    "androidx/cardview", "androidx/collection", "androidx/concurrent", "androidx/coordinatorlayout",
    "androidx/core", "androidx/cursoradapter", "androidx/customview", "androidx/documentfile",
    "androidx/drawerlayout", "androidx/dynamicanimation", "androidx/exifinterface", "androidx/fragment",
    "androidx/interpolator", "androidx/leanback", "androidx/legacy", "androidx/lifecycle",
    "androidx/loader", "androidx/localbroadcastmanager", "androidx/media", "androidx/mediarouter",
    "androidx/palette", "androidx/preference", "androidx/print", "androidx/recyclerview",
    "androidx/savedstate", "androidx/slice", "androidx/slidingpanelayout", "androidx/swiperefreshlayout",
    "androidx/transition", "androidx/vectordrawable", "androidx/versionedparcelable", "androidx/viewpager",
    "androidx/viewpager2", "androidx/activity", "androidx/startup", "androidx/tracing",
    "androidx/profileinstaller", "androidx/emoji2", "androidx/resourceinspection", "androidx/constraintlayout",
]


# 工具函数
def find_jar_source(config: AarConfig) -> Optional[Path]:
    """查找 JAR 文件源"""
    if config.jar_source:
        jar_path = Path(config.jar_source)
        if jar_path.exists():
            return jar_path
        return None
    
    base_path = AOSP_ROOT / "out/soong/.intermediates" / config.intermediate_path / "android_common"
    
    # 优先使用 combined JAR
    combined_jar = base_path / "combined" / f"{config.name}.jar"
    if combined_jar.exists():
        return combined_jar
    
    # 其次使用 javac JAR
    javac_jar = base_path / "javac" / f"{config.name}.jar"
    if javac_jar.exists():
        return javac_jar
    
    return None


def find_res_dirs(source_path: Path) -> List[Path]:
    """查找所有资源目录（排除 tests）"""
    res_dirs = []
    for root, dirs, files in os.walk(source_path):
        root_path = Path(root)
        # 排除测试目录
        if '/tests/' in str(root_path) or '/test/' in str(root_path):
            continue
        if root_path.name in ('res', 'res-private', 'res-keyguard', 'res-product'):
            res_dirs.append(root_path)
    return sorted(res_dirs)


def merge_values_xml(target_file: Path, source_file: Path) -> bool:
    """合并两个 values XML 文件的资源定义（追加新资源到已有文件）"""
    try:
        target_content = target_file.read_text(encoding='utf-8')
        source_content = source_file.read_text(encoding='utf-8')
    except Exception:
        return False
    
    # 提取 source 中的资源定义（在 <resources> 和 </resources> 之间的内容）
    match = re.search(r'<resources[^>]*>(.*?)</resources>', source_content, re.DOTALL)
    if not match:
        return False
    
    source_resources = match.group(1).strip()
    if not source_resources:
        return False
    
    # 在 target 的 </resources> 之前插入 source 的资源
    if '</resources>' in target_content:
        new_content = target_content.replace('</resources>', f'\n{source_resources}\n</resources>')
        target_file.write_text(new_content, encoding='utf-8')
        return True
    
    return False


def copy_res_dir(src_res_dir: Path, dst_res_dir: Path) -> tuple:
    """复制资源目录，对 values XML 进行合并"""
    copied_count = 0
    merged_count = 0
    
    for root, dirs, files in os.walk(src_res_dir):
        root_path = Path(root)
        rel_root = root_path.relative_to(src_res_dir)
        dst_root = dst_res_dir / rel_root
        dst_root.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            src_file = root_path / f
            dst_file = dst_root / f
            
            # 判断是否是 values 目录下的 XML 文件
            is_values_xml = ('values' in str(rel_root) or str(rel_root).startswith('values')) and f.endswith('.xml')
            
            if dst_file.exists():
                if is_values_xml:
                    # 合并 XML 内容
                    if merge_values_xml(dst_file, src_file):
                        merged_count += 1
                # 非 values XML 文件，如果已存在则跳过
            else:
                # 目标文件不存在，直接复制
                shutil.copy2(src_file, dst_file)
                copied_count += 1
    
    return copied_count, merged_count


def remove_duplicate_resources(res_dir: Path):
    """跨文件移除 values XML 文件中重复的资源定义"""
    # 收集所有 values 目录下的 XML 文件
    values_files = []
    for root, dirs, files in os.walk(res_dir):
        # 只处理 values* 目录
        if '/values' in root or root.endswith('/values') or '/values-' in root:
            for f in files:
                if f.endswith('.xml'):
                    values_files.append(Path(root) / f)
    
    # 按目录分组处理，同一个 values 目录下的文件共享去重状态
    dir_groups = {}
    for f in values_files:
        dir_name = str(f.parent)
        if dir_name not in dir_groups:
            dir_groups[dir_name] = []
        dir_groups[dir_name].append(f)
    
    # 处理每个目录组
    for dir_name, files in dir_groups.items():
        seen: Set[str] = set()  # 每个 values 目录独立的去重状态
        
        for xml_file in sorted(files):  # 排序确保处理顺序一致
            try:
                content = xml_file.read_text(encoding='utf-8')
            except Exception:
                continue
            
            result_lines = []
            in_resources = False
            skip_until_close = None
            
            for line in content.split('\n'):
                if '<resources' in line:
                    in_resources = True
                    result_lines.append(line)
                    continue
                if '</resources>' in line:
                    result_lines.append(line)
                    continue
                
                if not in_resources:
                    result_lines.append(line)
                    continue
                
                if skip_until_close:
                    if f'</{skip_until_close}>' in line:
                        skip_until_close = None
                    continue
                
                # 匹配资源定义开始
                match = re.search(
                    r'<(string|color|dimen|attr|style|array|integer|bool|id|item|fraction|drawable|plurals|declare-styleable|string-array|integer-array)[^>]*name="([^"]+)"',
                    line
                )
                if match:
                    res_type, res_name = match.group(1), match.group(2)
                    key = f"{res_type}:{res_name}"
                    if key in seen:
                        # 跳过重复定义
                        if '/>' not in line and f'</{res_type}>' not in line:
                            skip_until_close = res_type
                        continue
                    seen.add(key)
                
                result_lines.append(line)
            
            # 写回文件
            xml_file.write_text('\n'.join(result_lines), encoding='utf-8')
    
    print(f"  [OK] Deduplicated {len(values_files)} values XML files across {len(dir_groups)} directories")


def clean_jar(jar_path: Path, work_dir: Path, config: AarConfig) -> Path:
    """清理 JAR 文件，删除冲突的类"""
    extract_dir = work_dir / "jar_extract"
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # 解压 JAR
    with zipfile.ZipFile(jar_path, 'r') as zf:
        zf.extractall(extract_dir)
    
    # 删除 R.class 和 R$*.class
    for r_class in extract_dir.rglob("R.class"):
        r_class.unlink()
    for r_inner in extract_dir.rglob("R$*.class"):
        r_inner.unlink()
    
    # 删除通用冲突包
    for pkg in COMMON_PACKAGES_TO_REMOVE:
        pkg_path = extract_dir / pkg
        if pkg_path.exists():
            if pkg_path.is_dir():
                shutil.rmtree(pkg_path)
            else:
                # 处理通配符模式
                for p in extract_dir.glob(f"{pkg}*"):
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
    
    # 删除特定配置中指定的包
    if config.packages_to_remove:
        for pkg in config.packages_to_remove:
            pkg_path = extract_dir / pkg
            if pkg_path.exists():
                if pkg_path.is_dir():
                    shutil.rmtree(pkg_path)
                else:
                    pkg_path.unlink()
    
    # iconloader 特殊处理：保留 com/android/launcher3
    if config.name != "iconloader":
        launcher3_path = extract_dir / "com/android/launcher3"
        if launcher3_path.exists():
            shutil.rmtree(launcher3_path)
    
    # 统计类数量
    class_count = len(list(extract_dir.rglob("*.class")))
    
    # 重新打包
    classes_jar = work_dir / "classes.jar"
    with zipfile.ZipFile(classes_jar, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in extract_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(extract_dir)
                zf.write(file_path, arcname)
    
    print(f"  [OK] classes.jar ({class_count} classes)")
    return classes_jar


def generate_aar(config: AarConfig):
    """生成单个 AAR 并安装到 Maven 仓库"""
    print("=" * 50)
    print(f"Processing: {config.name}")
    
    work_dir = Path(tempfile.mkdtemp(prefix=f"aar_work_{config.name}_"))
    
    try:
        # 1. 处理 classes.jar
        jar_source = find_jar_source(config)
        if jar_source:
            print(f"  [INFO] Using JAR: {jar_source}")
            classes_jar = clean_jar(jar_source, work_dir, config)
        else:
            print(f"  [WARN] No JAR source found, creating empty classes.jar")
            classes_jar = work_dir / "classes.jar"
            with zipfile.ZipFile(classes_jar, 'w') as zf:
                zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        
        # 2. 合并资源
        res_dir = work_dir / "res"
        res_dir.mkdir(exist_ok=True)
        
        source_path = AOSP_ROOT / config.source_path
        res_dirs = find_res_dirs(source_path)
        
        total_copied = 0
        total_merged = 0
        for src_res in res_dirs:
            copied, merged = copy_res_dir(src_res, res_dir)
            total_copied += copied
            total_merged += merged
        
        print(f"  [OK] Merged {total_copied} files, {total_merged} XML merges from {len(res_dirs)} res dirs")
        
        # 删除特定资源
        if config.res_to_remove:
            for res_pattern in config.res_to_remove:
                res_path = res_dir / res_pattern
                if res_path.exists():
                    if res_path.is_dir():
                        shutil.rmtree(res_path)
                    else:
                        res_path.unlink()
                    print(f"  [INFO] Removed res/{res_pattern}")
        
        # 去重资源定义
        remove_duplicate_resources(res_dir)
        
        # 3. AndroidManifest.xml
        base_path = AOSP_ROOT / "out/soong/.intermediates" / config.intermediate_path / "android_common"
        manifest_sources = [
            base_path / "manifest_fixer" / "AndroidManifest.xml",
            source_path / "AndroidManifest.xml",
        ]
        
        manifest_dst = work_dir / "AndroidManifest.xml"
        manifest_found = False
        for manifest_src in manifest_sources:
            if manifest_src.exists():
                shutil.copy(manifest_src, manifest_dst)
                manifest_found = True
                break
        
        if not manifest_found:
            manifest_dst.write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                f'package="com.android.{config.name.lower().replace("-", "")}"/>\n'
            )
        
        # 4. R.txt (可选)
        r_txt_src = base_path / "R.txt"
        if r_txt_src.exists():
            shutil.copy(r_txt_src, work_dir / "R.txt")
        
        # 5. 打包 AAR
        aar_file = work_dir / f"{config.name}-{VERSION}.aar"
        with zipfile.ZipFile(aar_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(classes_jar, "classes.jar")
            zf.write(manifest_dst, "AndroidManifest.xml")
            
            r_txt = work_dir / "R.txt"
            if r_txt.exists():
                zf.write(r_txt, "R.txt")
            
            for res_file in res_dir.rglob("*"):
                if res_file.is_file():
                    arcname = "res" / res_file.relative_to(res_dir)
                    zf.write(res_file, str(arcname))
        
        # 6. 安装到 Maven 仓库
        group_path = GROUP_ID.replace(".", "/")
        maven_dir = MAVEN_REPO / group_path / config.name / VERSION
        maven_dir.mkdir(parents=True, exist_ok=True)
        
        shutil.copy(aar_file, maven_dir / f"{config.name}-{VERSION}.aar")
        
        # 生成 POM 文件
        pom_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"
    xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{GROUP_ID}</groupId>
  <artifactId>{config.name}</artifactId>
  <version>{VERSION}</version>
  <packaging>aar</packaging>
</project>
'''
        (maven_dir / f"{config.name}-{VERSION}.pom").write_text(pom_content)
        
        size = aar_file.stat().st_size / 1024
        print(f"  [SUCCESS] Installed to Maven: {GROUP_ID}:{config.name}:{VERSION} ({size:.0f}K)")
        print(f"            Path: {maven_dir}")
        
    finally:
        shutil.rmtree(work_dir)


def verify_aar_resources(aar_path: Path, config: AarConfig) -> List[str]:
    """验证 AAR 资源完整性：检查 classes.jar 中引用的 R 类是否有对应资源"""
    warnings = []
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        
        # 解压 AAR
        with zipfile.ZipFile(aar_path, 'r') as zf:
            zf.extractall(tmp_dir)
        
        classes_jar = tmp_dir / "classes.jar"
        res_dir = tmp_dir / "res"
        
        if not classes_jar.exists():
            return warnings
        
        # 解压 classes.jar 并查找对 R 类的引用
        jar_extract = tmp_dir / "jar"
        with zipfile.ZipFile(classes_jar, 'r') as zf:
            zf.extractall(jar_extract)
        
        # 收集 res 中实际存在的资源类型
        existing_res_types = set()
        if res_dir.exists():
            for item in res_dir.iterdir():
                if item.is_dir():
                    # values-xx -> values, drawable-hdpi -> drawable
                    res_type = item.name.split('-')[0]
                    existing_res_types.add(res_type)
        
        # 检查 R.txt 中声明的资源类型
        r_txt = tmp_dir / "R.txt"
        declared_res_types = set()
        if r_txt.exists():
            for line in r_txt.read_text().splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    declared_res_types.add(parts[1])  # int xml xxx -> xml
        
        # 资源类型映射（某些资源不需要对应目录）
        no_dir_needed = {'id', 'attr', 'styleable', 'style'}
        
        for res_type in declared_res_types:
            if res_type in no_dir_needed:
                continue
            if res_type not in existing_res_types and res_type != 'values':
                # values 资源在 values/ 目录下，但类型名可能是 string, color 等
                if res_type not in ['string', 'color', 'dimen', 'bool', 'integer', 'array']:
                    warnings.append(f"资源类型 '{res_type}' 在 R.txt 中声明但 res/{res_type}/ 目录不存在")
    
    return warnings


def main():
    print(f"AOSP Root: {AOSP_ROOT}")
    print(f"Maven Repo: {MAVEN_REPO}")
    print(f"Group ID: {GROUP_ID}")
    print(f"Version: {VERSION}")
    print()
    
    # 清空并重建 Maven 仓库
    if MAVEN_REPO.exists():
        shutil.rmtree(MAVEN_REPO)
    MAVEN_REPO.mkdir(parents=True)
    
    # 生成所有 AAR
    all_warnings = []
    for config in AAR_CONFIGS:
        generate_aar(config)
        
        # 验证生成的 AAR
        group_path = GROUP_ID.replace(".", "/")
        aar_path = MAVEN_REPO / group_path / config.name / VERSION / f"{config.name}-{VERSION}.aar"
        if aar_path.exists():
            warnings = verify_aar_resources(aar_path, config)
            if warnings:
                all_warnings.append((config.name, warnings))
    
    # 输出验证结果
    if all_warnings:
        print()
        print("=" * 50)
        print("⚠️  资源完整性警告:")
        for name, warnings in all_warnings:
            print(f"\n  {name}:")
            for w in warnings:
                print(f"    - {w}")
    
    print()
    print("=" * 50)
    print("Maven Repository Structure:")
    for aar_file in sorted(MAVEN_REPO.rglob("*.aar")):
        print(f"  {aar_file.relative_to(MAVEN_REPO)}")
    
    print()
    print("=" * 50)
    print("Usage in build.gradle.kts:")
    print()
    print('// In settings.gradle.kts:')
    print('repositories {')
    print('    maven { url = uri("${rootProject.projectDir}/libs/maven") }')
    print('}')
    print()
    print('// In build.gradle.kts:')
    print('dependencies {')
    for config in AAR_CONFIGS:
        print(f'    implementation("{GROUP_ID}:{config.name}:{VERSION}")')
    print('}')


if __name__ == "__main__":
    main()
