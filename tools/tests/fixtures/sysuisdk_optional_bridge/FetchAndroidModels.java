import java.io.File;
import java.util.ArrayList;
import java.util.List;
import org.gradle.tooling.*;
import org.gradle.tooling.model.gradle.BasicGradleProject;
import com.android.builder.model.v2.models.AndroidProject;

// Tooling API client, not an Android production/test source. Compile separately
// as documented in README.md. Assert all current Android modules retain Debug
// UnitTest artifacts and resolve their actual AGP mockable platform JAR.
public class FetchAndroidModels {
    public static class Fetch implements BuildAction<List<String>> {
        public List<String> execute(BuildController controller) {
            List<String> records = new ArrayList<>();
            for (BasicGradleProject project : controller.getBuildModel().getProjects()) {
                AndroidProject model = controller.findModel(project, AndroidProject.class);
                if (model == null) continue;
                for (var variant : model.getVariants()) {
                    if (variant.getHostTestArtifacts().isEmpty()) {
                        if (variant.getName().equals("debug")) throw new IllegalStateException("Debug UnitTest missing: " + project.getPath());
                        records.add(project.getPath() + " " + variant.getName() + " hostTests=none");
                        continue;
                    }
                    if (!variant.getHostTestArtifacts().containsKey("_unit_test_")) {
                        throw new IllegalStateException("UnitTest missing: " + project.getPath() + " " + variant.getHostTestArtifacts().keySet());
                    }
                    var artifact = variant.getHostTestArtifacts().get("_unit_test_");
                    File jar = artifact.getMockablePlatformJar();
                    if (jar == null || !jar.isFile()) throw new IllegalStateException("Mockable JAR missing");
                    records.add(project.getPath() + " " + variant.getName() + " unitTest=" + jar);
                }
            }
            if (records.size() != 26) throw new IllegalStateException("Expected 13 Android modules x 2 variants, got " + records.size());
            return records;
        }
    }
    public static void main(String[] args) {
        var connector = GradleConnector.newConnector().forProjectDirectory(new File(args[0]));
        connector.useInstallation(new File(args[1]));
        try (var connection = connector.connect()) {
            var action = connection.action(new Fetch())
                .withArguments("--offline", "--stacktrace", "--console=plain")
                // AGP's static BootClasspathBuilder cache omits the SDK root.
                // Never reuse a daemon that may have seen another SDK directory.
                .setJvmArguments("-Xmx16g", "-Dfile.encoding=UTF-8", "-XX:-OmitStackTraceInFastThrow",
                    "-Dsysuisdk.model.probe=" + java.util.UUID.randomUUID())
                .setStandardOutput(System.out).setStandardError(System.err);
            for (String record : action.run()) System.out.println("MODEL_PASS " + record);
            System.out.println("ALL_ANDROID_MODELS_PASS");
        }
    }
}
