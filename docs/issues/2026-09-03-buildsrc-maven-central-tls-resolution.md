# buildSrc Maven Central TLS dependency resolution failure

Date: 2026-09-03

## Background

A fresh Gradle 9.5.0 configuration run downloads most plugins and Android Gradle Plugin artifacts through the Tencent Cloud mirrors, but `:buildSrc:compileKotlin` fails while resolving:

`org.jetbrains.kotlin:kotlin-assignment-compiler-plugin-embeddable:2.2.10`

The failing request goes directly to Maven Central:

`https://repo.maven.apache.org/maven2/...`

and ends with `SSLHandshakeException: Remote host terminated the handshake` / `EOFException: SSL peer shut down incorrectly`.

The same log also contains a separate compatibility warning: Gradle 9.5 embeds Kotlin 2.3.20 while `buildSrc` explicitly requests Kotlin 2.2.10 alongside `kotlin-dsl`. That warning is not yet established as the cause of this network-resolution failure.

## Plan

1. Inspect root and `buildSrc` repository/plugin declarations and preserve existing user changes.
2. Build a narrow, repeatable dependency-resolution probe for `:buildSrc:kotlinCompilerPluginClasspathMain`.
3. Test ranked causes one variable at a time: direct Maven Central reachability, repository ordering/content, then Kotlin plugin alignment if still relevant.
4. Apply the smallest repository/configuration fix and rerun the narrow probe.
5. Run `./gradlew help` as the configuration-level regression check; do not run a full APK build unless needed.

## Error-count evolution

- Initial report: 1 dependency-resolution failure before source compilation; Kotlin/source error count is not applicable.
- First post-change probe exposed the second half of the same boundary: dependency repositories used the Tencent mirror, but `kotlin-dsl` plugin resolution still fell through to `plugins.gradle.org` and hit the same TLS failure.
- Final narrow configuration probe: 0 dependency-resolution/TLS failures; `./gradlew help --refresh-dependencies --console=plain --info` completed successfully.

## Findings

1. `buildSrc` is an independent build. Its dependencies did not inherit the root build's mirror declarations, so its Kotlin compiler-plugin artifacts were fetched through direct `mavenCentral()`.
2. Plugin resolution is a separate repository boundary. Adding dependency mirrors only to `buildSrc/build.gradle.kts` fixed the originally reported Maven artifact path, but a forced refresh then demonstrated that the `kotlin-dsl` marker/implementation could still fall through to direct `plugins.gradle.org`.
3. Both exact artifacts are present on the Tencent mirrors:
   - `kotlin-assignment-compiler-plugin-embeddable:2.2.10` on `maven-public` returned HTTP 200.
   - Gradle Kotlin DSL plugin marker and implementation 6.5.7 on `gradle-plugins` returned HTTP 200.
4. Direct Maven Central connectivity is unhealthy in the current environment (the exact POM request timed out), while the Tencent URL succeeds. The Gradle TLS wording is generic; enabling older TLS versions is neither necessary nor appropriate.
5. The Gradle 9.5 embedded-Kotlin 2.3.20 versus requested Kotlin 2.2.10 warning remains. It is non-fatal and independent from the TLS failure; changing the pinned Kotlin/AGP version matrix requires a separate decision.

## Implementation

- Added Tencent and Aliyun dependency mirrors before `google()` / `mavenCentral()` in `buildSrc/build.gradle.kts`.
- Added `buildSrc/settings.gradle.kts` so `kotlin-dsl` plugin resolution also uses Tencent/Aliyun plugin mirrors before the Gradle Plugin Portal fallback.
- Preserved the user's pre-existing `gradle.properties` change (`org.gradle.tooling.parallel=true`).

## Verification

- `./gradlew help --refresh-dependencies --console=plain --info` → **BUILD SUCCESSFUL in 48s**.
- The exact originally failing `kotlin-assignment-compiler-plugin-embeddable:2.2.10` POM and JAR resolved from Tencent `maven-public`.
- Successful probe log contained 0 `repo.maven.apache.org`, 0 `plugins.gradle.org`, and 0 TLS/handshake failure occurrences.
- `./gradlew -p buildSrc test --refresh-dependencies --console=plain` reached compilation and ran all 11 tests without a repository/TLS failure: 10 passed; the sole failure was the known host prerequisite `/home/conv/myspace/aosp/.../repackaging.txt` being absent on macOS, unrelated to this change.
- Full APK build was not run because the failure was configuration/dependency resolution and the narrower `help --refresh-dependencies` probe exercised the affected path.

## Open questions

- The non-fatal Kotlin compatibility warning should be reviewed separately if the project later changes Gradle/AGP/Kotlin versions; it should not be “fixed” by an unapproved version change as part of this network issue.
