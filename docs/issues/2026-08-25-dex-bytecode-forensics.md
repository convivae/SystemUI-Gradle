# Task 053 — DEX Bytecode Forensics: duplicate `NotificationLockscreenUserManagerImpl` (NLSUMI)

**Date**: 2026-08-25 · **Worker**: herdr task053 · **Mode**: read-only static forensics (no builds, no source edits)

**Analyzed artifact**: `app/build/outputs/apk/debug/app-debug.apk` `classes4.dex`
SHA-256 `5b716f53…` (byte-identical copy staged at `/tmp/dex-audit/apk-dex/classes*.dex`, 24 dex files).
The APK **contains the task053 `SysUIDup` instrumentation strings**, and runtime line numbers in the
trace match the current on-disk KSP generated sources — the trace IS this build (per architect re-check).
dexdump: `/home/conv/Android/Sdk/build-tools/37.0.0/dexdump`.

---

## Verdict summary

| Verdict | Question | Result |
|---|---|---|
| **Verdict A** | Does the scoped path (fact 3) exist and is it properly wired in the DEX? | **YES — and it is the ONLY NLSUMI construction path in the entire APK.** One raw factory, one `DoubleCheck`, one `DelegateFactory` field; all 25 consumers read the shared field. |
| **Verdict B** | Does KSP2 codegen differ semantically from the AOSP kapt reference for these bindings? | **NO.** kapt uses `SwitchingProvider` codegen, KSP uses per-class `_Factory` classes; scoping of all 8 target bindings is semantically identical. KSP debug vs release component are structurally identical (only `featureFlagsClassicDebugProvider`/`ReleaseProvider` naming + ~11-line offset). |
| **Verdict C** | Is there a second / unscoped NLSUMI construction path in the DEX? | **NO. Exhaustively excluded across all 24 dex files.** Within one `ReferenceSysUIComponentImpl` instance the bytecode makes a second NLSUMI construction **impossible** through any static path. The runtime duplication must be dynamic — see "Root cause" below. |

---

## 1. Verdict A — the scoped path, proven from bytecode

### 1.1 The construction site (classes4.dex, `ReferenceSysUIComponentImpl.initialize72`)

`NotificationLockscreenUserManagerImpl_Factory.create(...)` is invoked **exactly once in the whole
APK** (all-dex proof in §3.1):

```
104650: 0a2e88: 7714 8828 0300  |014a: invoke-static/range {v3..v22},
   Lcom/android/systemui/statusbar/NotificationLockscreenUserManagerImpl_Factory;.create:(
     Ldagger/internal/Provider; ×20 )Lcom/android/systemui/statusbar/NotificationLockscreenUserManagerImpl_Factory; // method@2888
104652: 0a2e90: … DoubleCheck.provider(raw factory)
104654: 0a2e98: 7120 9938 2100  |0152: invoke-static {v1, v2},
   Ldagger/internal/DelegateFactory;.setDelegate:(Ldagger/internal/Provider;Ldagger/internal/Provider;)V // method@3899
```

Field lifecycle (exactly **one `iput`** in the whole dex — no reassignment possible):

```
103658: 0a219c: 5be0 1f0c |0068: iput-object v0, v14,
  …ReferenceSysUIComponentImpl;.notificationLockscreenUserManagerImplProvider:Ldagger/internal/Provider; // field@0c1f
      (initialize7: field = new DelegateFactory — cycle-breaking declaration site)
… initialize72 @0a2e88: raw factory created → @0a2e90 DoubleCheck.provider(...) → @0a2e98 setDelegate(field, doubleCheck)
```

Corresponding KSP source (`SystemUI-core/build/generated/ksp/debug/java/com/android/systemui/dagger/DaggerReferenceGlobalRootComponent.java:18032`):

```java
DelegateFactory.setDelegate(notificationLockscreenUserManagerImplProvider,
    DoubleCheck.provider(NotificationLockscreenUserManagerImpl_Factory.create(
        contextProvider, broadcastDispatcherProvider, …, dumpManagerProvider, …)));
```

### 1.2 NLSUMI's own `<init>` is invoked exactly once in the APK

classes2.dex @0d2a9c, inside `NotificationLockscreenUserManagerImpl_Factory.newInstance`
(`invokespecial …<init>`). No other dex file even contains the NLSUMI class descriptor
(§3.1) — no direct `new`, no reflection target, no other factory.

### 1.3 Every consumer goes through the shared DelegateFactory field

25 `iget` sites of `notificationLockscreenUserManagerImplProvider` in classes4.dex — **all inside
`initialize*` methods as factory arguments**; there is **no accessor/provision method** on
`ReferenceSysUIComponentImpl` exposing NLSUMI (any such method would `iget` the field too):

```
initialize  0891f0   initialize2 0896ac 0896e8   initialize15 0942bc 094598
initialize17 094b66 094be2       initialize20 095920          initialize33 0988de
initialize43 09af80 09b064       initialize47 09c4f2          initialize48 09c6f4 09c788 09c972
initialize62 0a03e0  initialize63 0a0950 0a0a32   initialize64 0a0e7a
initialize7  0a224c  initialize72 0a2dfc 0a2ec2   initialize74 0a3c36 0a3c9e   initialize98 0a983c
```

The 19 consuming bindings (from KSP source; each receives the field as a `Provider` arg):

`HideNotifsForOtherUsersCoordinator`, `ViewConfigCoordinator`, `SensitiveContentCoordinatorImpl`,
`NotificationRemoteInputManager`, `LegacyMediaDataFilterImpl`, `MediaDataFilterImpl`,
`MediaControlPanel`, `CameraGestureHelper`, `NotificationRowBinderImpl`,
`LockscreenShadeTransitionController`, `DynamicPrivacyController`,
`KeyguardNotificationVisibilityProviderImpl`, `StatusBarRemoteInputCallback`,
`StatusBarNotificationPresenter`, `StatusBarNotificationActivityStarter`,
`ActivityStarterInternalImpl`, **`LegacyActivityStarterInternalImpl`** (fact-3 path, param #16,
eager `Provider`), `KeyguardBypassController` (via `DoubleCheck.lazy`), `NotifUiAdjustmentProvider`.

The observed fact-3 chain (`LASI_Factory.get(:157) → DelegateFactory.get → DoubleCheck.get →
getSynchronized → NLSUMI_Factory.get(:131)`) matches this wiring frame-for-frame.

**Verdict A: the scoped path exists and is the sole path. Within one component instance,
NLSUMI is singleton-cached by `DoubleCheck`.**

---

## 2. Verdict B — KSP2 vs AOSP kapt reference (`kapt-sources.jar`)

AOSP kapt (`out/soong/.intermediates/…/SystemUI-core/android_common/kapt/kapt-sources.jar`,
`DaggerReferenceGlobalRootComponent.java`, 25738 lines) uses Dagger **fastInit/SwitchingProvider**
codegen; KSP2 uses classic per-class factories. Per-binding scoping is semantically identical:

| Binding | kapt (SwitchingProvider case) | KSP2 (this APK) | Equivalent? |
|---|---|---|---|
| NLSUMI | `DelegateFactory` + `setDelegate(DoubleCheck.provider(SwitchingProvider …, 95))` (L17362); case 95 inlines `new NLSUMI(…)` (L18921) | `DelegateFactory` (init7 @0a219c) + `setDelegate(DoubleCheck.provider(NLSUMI_Factory.create(…)))` (init72 @0a2e88-0a2e98) | ✅ same scoping |
| LegacyActivityStarterInternalImpl | `DoubleCheck.provider(SwitchingProvider …, 1230)` (L17579) | direct `DoubleCheck(LASI_Factory.create(…))` (init74 @0a3cf2, iput field@0b1f) | ✅ |
| ShadeInteractorImpl | `DelegateFactory` + `setDelegate(DoubleCheck(SP 182))` (L15552/17294) | **direct `DoubleCheck(ShadeInteractorImpl_Factory.create(…))`** (init7 @0a213c) | ✅ (KSP does not need cycle-break here) |
| UserSwitcherInteractor | `DelegateFactory` + `DoubleCheck(SP 57)` (L15704/17582) | `DelegateFactory` + setDelegate (init73 @0a34fe/0a350e) | ✅ |
| ActivityStarterImpl | `DelegateFactory` + `DoubleCheck(SP 59)` (L15645/17580) | `DelegateFactory` + setDelegate (init74 @0a3d1e/0a3d2e) | ✅ |
| `PrivacyDotViewControllerImpl.Factory` (assisted) | `factoryProvider115 = SingleCheck.provider(SP 1436)`; case 1436 returns an anonymous Factory whose `create()` calls `new PrivacyDotViewControllerImpl(… shadeInteractorImplProvider.get() …)` (L17998/23665-23673) | raw `privacyDotViewControllerImplProvider` field (init76 @0a4168) + `factoryProvider110 = InstanceFactory.create(new _Factory_Impl(raw))` (@0a4170/0a4178) | ✅ (single shared impl; `create()` unscoped by assisted-factory design) |
| `PrivacyDotViewController` (`@SysUISingleton controller`) | `controllerProvider2 = DoubleCheck.provider(SP 1435)` (L17999) | `controllerProvider2 = DoubleCheck.provider(ControllerFactory.create(…))` (init76 @0a4190) | ✅ scoped |
| ScreenDecorations | `screenDecorationsProvider` (DoubleCheck) in startables map `put(ScreenDecorations.class, …)` | `screenDecorationsProvider = DoubleCheck(ScreenDecorations_Factory.create(…))` (init79 @0a4dcc-0a4de6); startables map puts the **DoubleCheck-wrapped field** (KSP L14550/L20027) | ✅ scoped |

Eager/lazy topology also matches: NLSUMI takes `Lazy<NotificationVisibilityProvider>`,
`Lazy<CommonNotifCollection>`, `Lazy<OverviewProxyService>`, `Lazy<DeviceUnlockedInteractor>`
(`NotificationLockscreenUserManagerImpl_Factory.newInstance` signature, KSP file lines 155-170);
all four cycle-closing edges are inert during construction in both variants.
`UserSwitcherInteractor_Factory.get(:125)` eagerly calls `activityStarterProvider.get()`
(param type `Provider<ActivityStarter>`, line 50/86) — matches trace.

**Verdict B: no variant-specific unscoped branch. KSP2 codegen is not the culprit;
release variant is structurally identical, so no build-type divergence.**

---

## 3. Verdict C — all-dex proof that NO second static path exists

### 3.1 String-reference census across all 24 dex files

An invoke of a method requires the defining class descriptor string in the same dex. Census
(`grep -c` on raw dex binaries):

| Symbol | dex files containing it |
|---|---|
| `NotificationLockscreenUserManagerImpl_Factory` | **classes2** (definition; `<init>` invoke @0d2a9c) · **classes4** (1 ref = the create invoke @0a2e88) |
| `Lcom/android/systemui/statusbar/NotificationLockscreenUserManagerImpl;` | **classes2** (2: def + `<init>` invoke) · **classes4** (1: field/create type) |
| `DaggerReferenceGlobalRootComponent;->builder` | **classes4** (2: def refs) · **classes7** (1 call site @08bc54, `SystemUIInitializerImpl.getGlobalRootComponentBuilder`) |
| `SysUIComponent$Builder` | **classes4** (2: def refs) · **classes7** (1 build call, `SystemUIInitializer.init` @08be3c) |
| `DaggerReferenceGlobalRootComponent` (any) | **classes4 only** |

Consequences:

1. **One component-build call site in the entire APK**: `SystemUIInitializer.init()` (classes7
   @08bdd8…; `builder.build()` @08be3c). `init()` itself is called from exactly one place:
   `SystemUIAppComponentFactoryBase.createSystemUIInitializerInternal` (classes7 @08ab18), behind
   the static memoization `systemUIInitializer ?: run { … }` (sget @08aa3e / sput @08ab2e).
2. **One root-builder call site** (classes7 @08bc54). Only `PhoneSystemUIAppComponentFactory`
   extends the base factory. `DaggerReferenceGlobalRootComponent` is the only Dagger root
   component class in the APK.
3. **One raw NLSUMI factory instance** can ever exist per component (single create invoke),
   wrapped in one `DoubleCheck`, installed via one `setDelegate`, on a field written exactly once.

### 3.2 Exclusion of every duplication mechanism that could act within one component

| Candidate mechanism | Bytecode verdict |
|---|---|
| Second `NLSUMI_Factory.create` invoke / raw-factory consumer | **Excluded** — §3.1: single invoke @0a2e88; all 25 consumers iget the DelegateFactory field; no accessor exists. |
| Field reassignment (fresh cache installed later) | **Excluded** — exactly one `iput` to the field (initialize7 @0a219c). `setDelegate` would throw on a second call. |
| Direct `new NLSUMI(…)` outside the factory | **Excluded** — `<init>` invoked only in classes2 `newInstance` (@0d2a9c); descriptor absent from all other dex. |
| Second `ReferenceSysUIComponentImpl` / second build site | **Excluded** — single `SysUIComponent$Builder.build()` call site (classes7 @08be3c); single root builder site (@08bc54); impl class exists only in classes4. |
| Same-thread re-entrant `DoubleCheck.get()` (Java monitors are reentrant; inner re-entry sees `instance==UNINITIALIZED`) | **Excluded for NLSUMI** — its only cycle-closing constructor deps are `Lazy` (visibilityProvider, notifCollection, overviewProxyService, deviceUnlockedInteractor); no eager path from its constructor back to the NLSUMI DoubleCheck. (A re-entrant cycle would also duplicate the *first* re-entered DoubleCheck in the loop, not NLSUMI.) |
| KSP-vs-kapt codegen divergence | **Excluded** — Verdict B. |
| Build-variant divergence (debug vs release) | **Excluded** — KSP debug/release components structurally identical for all 8 bindings. |

### 3.3 What remains: the second construction must be DYNAMIC, not static

Given the runtime facts (one initializer, one root hash, one DumpManager hash, 3 NLSUMI
instances, crash at 2nd registration with `alreadyRegistered=true`), the only
bytecode-consistent mechanism left is:

> **`DoubleCheck` never caches because NLSUMI construction #1 *throws after* `registerDumpable`.**
> `DoubleCheck.get()` only writes `instance` after `provider.get()` returns normally.
> NLSUMI's constructor (`NotificationLockscreenUserManagerImpl.java:294-346`) calls
> `dumpManager.registerDumpable(this)` at **line 339 — before** the tail
> `if (keyguardPrivateNotifications()) init();` (lines 341-345). If construction #1
> registers successfully and then throws in the tail (`init()` registers two
> `ContentObserver`s via `mContext.getContentResolver().registerContentObserver(…, USER_ALL)`
> at lines ~402-412 and two broadcast receivers — any of which can throw at runtime, e.g.
> security/system errors during early boot), then:
> - the name stays in the DumpManager `TreeMap` (instance field, DumpManager.kt:53) forever,
>   pointing at the half-dead NLSUMI #1;
> - `DoubleCheck.instance` stays `UNINITIALIZED`;
> - **every subsequent** `get()` constructs a *new* NLSUMI, which dies at line 339 with
>   `IllegalArgumentException("'…' is already registered")` — the observed crash loop,
>   one root, one DumpManager, 3 distinct NLSUMI hashes.

This fits every stated runtime fact and requires no second component, no second factory and no
unscoped binding. It also explains why the visible crash surfaces inside the
`ScreenDecorations → PDVC → ShadeInteractor → UserSwitcherInteractor → ActivityStarterImpl →
LASI → NLSUMI` chain (fact 4): that chain is simply the *first* eager consumer to re-enter the
poisoned (uncached) NLSUMI binding after construction #1 failed.

**Corollary prediction (testable with the already-deployed SysUIDup instrumentation):**
logcat must contain a *first* exception whose bottom frame is inside
`NotificationLockscreenUserManagerImpl.<init>` **after** line 339 (i.e. in
`keyguardPrivateNotifications()`/`init()` — ContentObserver or receiver registration),
*preceding* the first `alreadyRegistered=true` crash. If no such first exception exists in the full boot logcat, the fallback dynamic candidates, in descending plausibility, are: (i) an object-identity anomaly in `DoubleCheck` (excluded in principle — its field is a normal instance field, but provable only at runtime by logging `System.identityHashCode` of the DelegateFactory/DoubleCheck inside `DelegateFactory.get`), or (ii) classloader duplication of the Dagger classes (would normally produce distinct DumpManager/root hashes too, which contradicts the instrumentation, so this is remote).

---

## 4. The 8-factory table (all in classes4.dex unless noted)

| # | Factory | `.create` invoke site (offset / method) | Storage / wrapping | Scoping verdict |
|---|---|---|---|---|
| 1 | `ShadeInteractorImpl_Factory` | `initialize7` **0a213c** | iput `shadeInteractorImplProvider` @0a214c — direct `DoubleCheck.provider(...)` | scoped (no DelegateFactory needed) |
| 2 | `NotificationLockscreenUserManagerImpl_Factory` | `initialize72` **0a2e88** (sole invoke in APK) | field iput'd once @0a219c (DelegateFactory); `DoubleCheck` @0a2e90; `setDelegate` @0a2e98 | scoped; sole path |
| 3 | `UserSwitcherInteractor_Factory` | `initialize73` **0a34fe** | DelegateFactory field; `setDelegate` @0a350e | scoped |
| 4 | `LegacyActivityStarterInternalImpl_Factory` | `initialize74` **0a3cf2** (26-arg create) | iput `legacyActivityStarterInternalImplProvider` field@0b1f — direct `DoubleCheck` | scoped |
| 5 | `ActivityStarterImpl_Factory` | `initialize74` **0a3d1e** (args v2-v5) | DelegateFactory field; `setDelegate` @0a3d2e | scoped |
| 6 | `PrivacyDotViewControllerImpl_Factory` | `initialize76` **0a4160** (5 args: mainExecutor, statusBarStateController, animScheduler, shadeInteractorImplProvider field@0f37, screenDecorationsDelayableExecutor) | iput `privacyDotViewControllerImplProvider` field@0ca6 @0a4168 — **raw, no DoubleCheck** (raw per-instance factory; see #7) | factory object itself unscoped, but only one instance exists per component; NLSUMI feed inside it is the shared DelegateFactory field |
| 7 | `PrivacyDotViewControllerImpl_Factory_Impl` (assisted-factory impl) | `initialize76` **0a4170** (`new _Impl(raw #6)`) → `factoryProvider110 = InstanceFactory.create(...)` @0a4178 | `InstanceFactory` (unscoped holder, but #6 is the single shared instance); 3 consumers: `ControllerFactory.create` (iget @0a417c), `MultiDisplayPrivacyDotViewControllerStore_Factory.create` (iget @0a41c4, init76), `ScreenDecorations_Factory.create` (iget @0a4dc8, init79) | assisted `create()` intentionally constructs a new PDVC per call — that is by design and does NOT touch NLSUMI's cache |
| 8 | `ScreenDecorations_Factory` | `initialize79` **0a4dcc** | `screenDecorationsProvider = DoubleCheck.provider(...)` (0a4dcc-0a4de6); startables map puts the DoubleCheck field (KSP L14550/L20027); `controllerProvider2 = DoubleCheck(ControllerFactory.create(...))` @0a4190 (init76) | scoped |

Definitions: `PrivacyDotViewControllerImpl_Factory`, `_Impl` and `ControllerFactory` are in **classes7.dex** (classes7.dexdump.txt lines 302433/302618). `_Impl.createFactoryProvider` = `InstanceFactory.create(new _Factory_Impl(delegateFactory))` — unscoped by assisted-factory contract, matching kapt's anonymous-Factory codegen (Verdict B).

## 5. Reproduction

```bash
# artifacts (scratch, read-only project):
#   /tmp/dex-audit/apk-dex/classes*.dex        (extracted from app-debug.apk; classes4 sha256 5b716f53…)
#   /tmp/dex-audit/classes4.dexdump.txt        dexdump -d output, parsed by parse_dexdump.py
#   /tmp/dex-audit/classes7.dexdump.txt        (475,735 lines)
#   /tmp/dex-audit/{parse_dexdump,extract_methods,scan_all,query_refs,query2,query6,query7}.py
#   /tmp/dex-audit/kapt-src/                   (extracted AOSP kapt-sources.jar)
# key greps used:
dexdump -d classes4.dex > classes4.dexdump.txt
grep -c NotificationLockscreenUserManagerImpl_Factory classes*.dex   # → classes2:3, classes4:1 only
# offsets quoted above are the "NNNNNN:" hex file offsets in dexdump -d output and are stable.
```

## 6. Residual notes for the runtime owner

- The `SysUIDup` TEMP-DEBUG instrumentation is present in the working tree (uncommitted,
  `CONV_ADD` blocks in `SystemUIAppComponentFactoryBase.kt`, `SystemUIInitializer.java`,
  `DumpManager.kt`) and in the analyzed APK.
- `DumpManager.dumpables` is an **instance** `TreeMap` (DumpManager.kt:53); the crash therefore
  guarantees one shared DumpManager instance, consistent with the instrumentation's single hash.
- This task's mandate was static DEX proof; §3.3's construction-throws hypothesis is the only
  mechanism consistent with both the bytecode (no static second path) and the runtime facts
  (one root / one DumpManager / 3 constructions). Confirming it requires reading the full boot
  logcat for the first post-line-339 exception — outside this read-only DEX task's scope.