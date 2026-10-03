# SysUISdk optional bridge integration fixture

This is a standalone **test project**, not a SystemUI production source module.
It exercises the installed AGP's real `testDebugUnitTest` pipeline. The Python
composition tests do not replace this gate. No platform stubs are supplied here.

From the repository root, against a generated SDK **root** containing build-tools:

```bash
ANDROID_HOME=/path/to/isolated/sdk ./gradlew \
  -p tools/tests/fixtures/sysuisdk_optional_bridge \
  testDebugUnitTest --no-daemon --rerun-tasks --console=plain
```

Do not create a fixture `local.properties` pointing at a different SDK: AGP gives
that file precedence over the environment. This fixture intentionally has none.
The AGP version matches the root project; JUnit coordinates match buildSrc's test
stack. They are upstream dependencies, not repackaged local JARs.

Acceptance: `build/test-results/testDebugUnitTest/TEST-validation.sdk.SdkBridgeTest.xml`
reports **4 tests, 0 failures, 0 errors, 0 skipped**. They cover:

- Java and Kotlin compile against the same real optional `IoUtils` definition;
- the runtime loads it from the SDK bridge JAR;
- host-safe `Chunk` code executes (its body was not replaced with a stub);
- a bridge enum's values/valueOf work after AGP's mockable conversion;
- ordinary Android APIs still use the AGP mockable library and throw `not mocked`.

This does not prove arbitrary libcore/ART native APIs execute on a host JVM, or
replace full-project Debug/Release, manifest and DEX boundary checks.
Those acceptance results live in `docs/CURRENT_STATE.md` and the dated issue.

## Full-project IDE model gate

`FetchAndroidModels.java` uses the public Gradle Tooling API to fetch AGP's actual
AndroidProject model for every Android module. It asserts 26 variant records
(13 modules), the Debug UnitTest artifact, and an existing resolved mockable JAR.
Release currently has no host test artifact by AGP default; it is not disabled
by this fix. This is a model gate, not a manual Studio UI interaction.

After the wrapper and AGP dependencies have been resolved, from the repo root:

```bash
probe=$(mktemp -d)
gradle_home=$(find "$HOME/.gradle/wrapper/dists/gradle-9.5.0-bin" -type d -name gradle-9.5.0 | head -1)
model_jar=$(find "$HOME/.gradle/caches/modules-2/files-2.1/com.android.tools.build/builder-model/9.3.1" -name builder-model-9.3.1.jar | head -1)
javac -cp "$gradle_home/lib/*:$model_jar" -d "$probe" \
  tools/tests/fixtures/sysuisdk_optional_bridge/FetchAndroidModels.java
java -cp "$probe:$gradle_home/lib/*:$gradle_home/lib/plugins/*:$model_jar" \
  FetchAndroidModels /path/to/project/using/isolated/sdk "$gradle_home"
```

The project argument must have `local.properties` / environment pointing to the
intended SDK. AGP 9.3.1 caches bootclasspath by API version/library requests, not
SDK root. The client requests a unique daemon JVM to avoid cross-SDK cache reuse;
the JVM fixture uses `--no-daemon` and checks the exact bridge path. Stop idle
Gradle daemons after SDK switching when no builds are running. The gate never
modifies the SDK path, test components, or build configuration. Old unsplit SDKs reproduce the original MockableJarTransform NPE;
missing optional libraries fail rather than silently removing tests.
