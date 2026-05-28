// JD MOD: Stub for platform RoleManager
package android.app.role;
public class RoleManager {
    public interface OnRoleHoldersChangedListener {
        void onRoleHoldersChanged(String roleName, java.util.List<android.os.UserHandle> users);
    }
    public void addOnRoleHoldersChangedListenerAsUser(java.util.concurrent.Executor executor, OnRoleHoldersChangedListener listener, android.os.UserHandle user) {}
    public void removeOnRoleHoldersChangedListenerAsUser(OnRoleHoldersChangedListener listener, android.os.UserHandle user) {}
    public java.util.List<String> getRoleHoldersAsUser(String roleName, android.os.UserHandle user) { return java.util.Collections.emptyList(); }
    public String getDefaultApplication(String roleName, android.os.UserHandle user) { return null; }
}
