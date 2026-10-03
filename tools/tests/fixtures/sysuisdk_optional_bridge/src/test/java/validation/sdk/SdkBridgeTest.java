package validation.sdk;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
import libcore.io.IoUtils;
import org.apache.harmony.dalvik.ddmc.Chunk;

class SdkBridgeTest {
    @Test void javaAndKotlinSeeTheSameRealBridge() throws Exception {
        assertSame(IoUtils.class, BridgeConsumerKt.bridgeClassFromKotlin());
        assertEquals(new java.io.File(System.getProperty("expectedBridgeJar")).getCanonicalFile(),
            new java.io.File(IoUtils.class.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile());
    }
    @Test void realHostSafeMethodBodyIsNotStubbed() {
        byte[] bytes = new byte[] {1, 2, 3};
        Chunk chunk = new Chunk(42, bytes, 1, 2);
        assertEquals(42, chunk.type);
        assertSame(bytes, chunk.data);
        assertEquals(1, chunk.offset);
        assertEquals(2, chunk.length);
    }
    @Test void enumMethodsSurviveMockableConversion() {
        var values = com.android.tools.r8.keepanno.annotations.KeepItemKind.values();
        assertTrue(values.length > 0);
        assertSame(values[0], com.android.tools.r8.keepanno.annotations.KeepItemKind.valueOf(values[0].name()));
    }
    @Test void androidMethodsStillUseTheAgpMockableLibrary() {
        RuntimeException error = assertThrows(RuntimeException.class,
            () -> android.text.TextUtils.isEmpty("value"));
        assertTrue(error.getMessage().contains("not mocked"), error.getMessage());
    }
}
