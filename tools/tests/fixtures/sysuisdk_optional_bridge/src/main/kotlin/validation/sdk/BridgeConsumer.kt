package validation.sdk

// Compiles against SDK optional library, not a program or compileOnly dependency.
fun bridgeClassFromKotlin(): Class<*> = libcore.io.IoUtils::class.java
