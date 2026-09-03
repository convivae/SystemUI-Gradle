SysUISdk quick install
======================

1. Unzip this archive so that the ``android-SysUISdk`` directory lands
   inside the ``platforms`` directory of your Android SDK, i.e.:

       <your-sdk>/platforms/android-SysUISdk/

   Example:

       cd ~/Android/Sdk/platforms && unzip SysUISdk-android-17.0.0_r1-r1.zip

   If your SDK root is elsewhere, point ``sdk.dir`` in the project's
   ``local.properties`` (or the ``ANDROID_HOME`` / ``ANDROID_SDK_ROOT``
   environment variable) at it.

2. Verify the checksum before use (see the ``.sha256`` asset published
   next to this archive):

       sha256sum SysUISdk-android-17.0.0_r1-r1.zip

3. Build the project:

       ./gradlew :app:assembleDebug
       ./gradlew :app:assembleRelease

The project references this platform via ``compileSdkPreview = "SysUISdk"``;
no further configuration is needed once the directory is in place.

See NOTICE for provenance and licensing details of the archive contents.
