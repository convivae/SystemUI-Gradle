// JD MOD: Stub for platform @SystemApi DeviceConfig
package android.provider;
public class DeviceConfig {
    public static final String NAMESPACE_SYSTEMUI = "systemui";
    public static final String NAMESPACE_PRIVACY = "privacy";
    public static String getString(String namespace, String name, String defaultValue) { return defaultValue; }
    public static boolean getBoolean(String namespace, String name, boolean defaultValue) { return defaultValue; }
    public static int getInt(String namespace, String name, int defaultValue) { return defaultValue; }
    public static long getLong(String namespace, String name, long defaultValue) { return defaultValue; }
    public static float getFloat(String namespace, String name, float defaultValue) { return defaultValue; }
    public static boolean putString(String namespace, String name, String value) { return false; }
    public static void addOnPropertiesChangedListener(String namespace, OnPropertiesChangedListener listener) {}
    public static void removeOnPropertiesChangedListener(OnPropertiesChangedListener listener) {}
    public interface OnPropertiesChangedListener { void onPropertiesChanged(Properties properties); }
    public static class Properties {
        public String getNamespace() { return ""; }
        public boolean getBoolean(String name, boolean defaultValue) { return defaultValue; }
        public int getInt(String name, int defaultValue) { return defaultValue; }
        public long getLong(String name, long defaultValue) { return defaultValue; }
        public float getFloat(String name, float defaultValue) { return defaultValue; }
        public String getString(String name, String defaultValue) { return defaultValue; }
    }
}
