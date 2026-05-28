# SystemUI Gradle 构建系统迁移日志

## 目标
将 AOSP SystemUI 代码迁移到 Gradle 构建系统，使其：
- 完全独立于 AOSP 源码树
- 任何人下载代码后能直接编译运行
- 不使用符号链接
- 不修改全局 SDK 配置

## 已知问题与解决方案

### 问题 1: 平台隐藏 API 不可用
**现象**: 编译时找不到 `WindowManager.TRANSIT_CLOSE`、`@android.annotation.Nullable` 等平台隐藏 API
**原因**: `compileSdk=37` 使用的 SDK `android.jar` 不包含隐藏 API，而 AOSP 的 `framework.jar` 虽然包含但优先级低于 SDK
**解决方案**: 创建合并的 `android.jar`（SDK + framework.jar），通过 Gradle 脚本动态替换 SDK 的 android.jar

### 问题 2: Kotlin 编译任务不存在
**现象**: AGP 9.x 不为某些模块创建 `compileDebugKotlin` 任务
**原因**: AGP 9.x 内置 Kotlin 支持，但源码目录必须在配置阶段设置，不能在 `afterEvaluate` 中设置
**解决方案**: 使用 AGP 9.x 兼容的 API 配置源码目录

### 问题 3: Proto 文件导入路径错误
**现象**: Proto 文件使用 AOSP 风格的绝对导入路径
**原因**: 复制的 Proto 文件保留了 AOSP 的导入路径格式
**解决方案**: 修改 Proto 文件的导入路径为相对路径

### 问题 4: 缺少 Aconfig 标志类
**现象**: 代码引用 `com.android.systemui.flags.Flags` 等类但找不到
**原因**: AOSP 使用 aconfig 生成标志类，Gradle 项目中没有这些生成的类
**解决方案**: 创建标志存根模块，手动生成标志类

## 实施步骤

### 步骤 1: 创建合并的 android.jar ✅
- 提取 SDK 的 `android.jar` 和 AOSP 的 `framework.jar`
- 合并为一个 jar 文件（71MB）
- 放置在项目的 `libs/platform/android.jar`

### 步骤 2: 创建自定义 SDK 目录 ✅
- 在 `libs/sdk/` 创建最小化 SDK 目录结构
- 包含合并的 android.jar 和必要的元数据文件
- 包含 build-tools

### 步骤 3: 配置 AGP 使用自定义 SDK
- 创建 Gradle 脚本动态替换 SDK 的 android.jar
- 在编译前替换，编译后恢复
- 不修改全局 SDK 配置

### 步骤 4: 修复所有模块的源码目录配置
- 确保 Kotlin 文件能被 AGP 检测到
- 使用 AGP 9.x 兼容的 API

### 步骤 5: 修复 Proto 编译
- 修改 Proto 文件的导入路径
- 配置 protobuf 插件使用 nano 格式

### 步骤 6: 创建标志存根模块
- 解析 `.aconfig` 文件
- 生成 Java 标志类
- 创建 Gradle 模块

### 步骤 7: 添加缺失的依赖
- 添加 `keepanno-annotations`
- 配置 Room schema 导出
- 添加 Dagger 注解处理器

## 验证方法
每个步骤完成后运行：
```bash
# 检查模块是否能编译
./gradlew :模块名:compileDebugKotlin

# 检查完整构建
./gradlew :app:assembleDebug
```

## 重要约束
1. **不使用符号链接**: 所有源码必须直接复制到项目中
2. **不修改全局 SDK**: 不能替换或修改用户机器上的 SDK 文件
3. **项目独立性**: 任何人下载代码后能直接编译
4. **版本控制**: 所有必要的文件（包括合并的 jar）必须提交到 Git
