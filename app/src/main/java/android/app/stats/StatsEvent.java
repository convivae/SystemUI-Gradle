// JD MOD: Stub for platform StatsEvent
package android.app.stats;
public class StatsEvent {
    public static class Builder {
        public Builder setAtomId(int atomId) { return this; }
        public Builder writeString(String value) { return this; }
        public Builder writeInt(int value) { return this; }
        public Builder writeLong(long value) { return this; }
        public Builder writeBoolean(boolean value) { return this; }
        public Builder writeByteArray(byte[] value) { return this; }
        public StatsEvent build() { return new StatsEvent(); }
        public byte[] toByteArray() { return new byte[0]; }
    }
}
