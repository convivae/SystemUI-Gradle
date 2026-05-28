// JD MOD: Stub for platform StatsManager
package android.app.stats;
public class StatsManager {
    public static final int FLAG_PRESERVE_EVERYTHING = 0;
    public void setPullAtomCallback(String atomTag, long coolDownMillis, int[] uids, StatsPullAtomCallback callback) {}
    public void clearPullAtomCallback(String atomTag) {}
    public interface StatsPullAtomCallback {
        int onPullAtom(int atomTag, java.util.List<StatsEvent> data);
    }
}
