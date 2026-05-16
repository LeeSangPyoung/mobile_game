#!/bin/bash
set -e
cd /Users/leesp/workspace_game
cp prototype.html app/www/index.html
mkdir -p app/www/assets app/www/img
rsync -a --delete --delete-excluded \
  --exclude 'generals/battle_faces/' \
  --exclude 'generals/busts_extra_*/' \
  --exclude 'generals/busts_fast_170/' \
  --exclude 'generals/busts_new_170/' \
  --exclude 'generals/busts_original_*/' \
  --exclude 'generals/busts_real_samples/' \
  --exclude 'generals/faces_original_*/' \
  --exclude 'generals/mobile_fullbody*/' \
  assets/ app/www/assets/
rsync -a --delete img/    app/www/img/
cd app
npx cap sync android > /dev/null 2>&1
cd android
ANDROID_HOME=~/Library/Android/sdk ./gradlew assembleDebug -q
APK=app/build/outputs/apk/debug/app-debug.apk
ADB=~/Library/Android/sdk/platform-tools/adb
PKG=com.leesp.samgukgi
if ! "$ADB" install -r "$APK"; then
  echo "adb install -r failed; trying data-preserving reinstall..."
  if ! "$ADB" shell cmd package uninstall -k "$PKG" || ! "$ADB" install "$APK"; then
    echo "data-preserving reinstall failed; backing up data and doing a clean reinstall..."
    BACKUP="$(mktemp /tmp/${PKG}.data.XXXXXX.tar)"
    if "$ADB" shell run-as "$PKG" ls /data/data/"$PKG" >/dev/null 2>&1; then
      "$ADB" exec-out run-as "$PKG" tar -C /data/data/"$PKG" -cf - app_webview files shared_prefs > "$BACKUP" || rm -f "$BACKUP"
    fi
    "$ADB" shell cmd package uninstall "$PKG" || true
    "$ADB" install "$APK"
    if [ -s "$BACKUP" ]; then
      "$ADB" push "$BACKUP" /data/local/tmp/${PKG}.data.tar >/dev/null
      "$ADB" shell run-as "$PKG" tar -C /data/data/"$PKG" -xf /data/local/tmp/${PKG}.data.tar || true
      "$ADB" shell rm -f /data/local/tmp/${PKG}.data.tar
      rm -f "$BACKUP"
    fi
  fi
fi
# 캐시는 강제 종료로만 비움 (저장 데이터는 유지)
"$ADB" shell am force-stop "$PKG" >/dev/null
"$ADB" shell am start -n "$PKG"/.MainActivity
