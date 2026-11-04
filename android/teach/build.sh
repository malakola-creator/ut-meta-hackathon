#!/usr/bin/env bash
# Build the Point and say headset app without Gradle: javac -> d8 -> aapt2 -> zipalign -> apksigner.
#   JAVA_HOME=~/miniforge3/envs/ut-apk ANDROID_SDK=~/Android/Sdk ./build.sh        # writes build/point-and-say.apk
#   adb install -r build/point-and-say.apk
# The signing key is a local debug key (build/debug.keystore, git-ignored), made on the first build.
set -euo pipefail
cd "$(dirname "$0")"
SDK=${ANDROID_SDK:-$HOME/Android/Sdk}
BT=$SDK/build-tools/34.0.0
JAR=$SDK/platforms/android-34/android.jar
JH=${JAVA_HOME:-$HOME/miniforge3/envs/ut-apk}
rm -rf build/classes build/dex build/*.apk && mkdir -p build/classes build/dex
"$JH/bin/javac" -source 11 -target 11 -nowarn -classpath "$JAR" -d build/classes $(find src -name '*.java') 2>&1 | grep -v "bootstrap classpath" || true
"$BT/d8" --min-api 29 --lib "$JAR" --output build/dex $(find build/classes -name '*.class')
"$BT/aapt2" link -I "$JAR" --manifest AndroidManifest.xml -o build/unsigned.apk
(cd build/dex && zip -q ../unsigned.apk classes.dex)
"$BT/zipalign" -f 4 build/unsigned.apk build/aligned.apk
if [ ! -f build/debug.keystore ]; then
  "$JH/bin/keytool" -genkeypair -keystore build/debug.keystore -storepass android -keypass android -alias debug \
    -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=point-and-say debug" >/dev/null 2>&1
fi
"$BT/apksigner" sign --ks build/debug.keystore --ks-pass pass:android --key-pass pass:android --out build/point-and-say.apk build/aligned.apk
rm -f build/unsigned.apk build/aligned.apk
echo "built $(pwd)/build/point-and-say.apk"
