#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HTML="file://${ROOT}/marketing/playstore_creatives.html"
OUT="${ROOT}/marketing/exports"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

mkdir -p "$OUT"

render() {
  local board="$1"
  local size="$2"
  local file="$3"
  "$CHROME" \
    --headless=new \
    --disable-gpu \
    --disable-background-networking \
    --disable-component-update \
    --disable-sync \
    --metrics-recording-only \
    --no-first-run \
    --no-default-browser-check \
    --hide-scrollbars \
    --force-device-scale-factor=1 \
    --virtual-time-budget=1000 \
    --window-size="$size" \
    --screenshot="${OUT}/${file}" \
    "${HTML}?board=${board}" >/dev/null 2>&1
}

render icon 512,512 icon_512.png
render feature 1024,500 feature_graphic_1024x500.png
render shot1 1080,1920 screenshot_01_battle_control.png
render shot2 1080,1920 screenshot_02_unit_counter.png
render shot3 1080,1920 screenshot_03_recruit_prisoner.png
render shot4 1080,1920 screenshot_04_collect_200_generals.png
render shot5 1080,1920 screenshot_05_upgrade_power.png
render shot6 1080,1920 screenshot_06_chapter_map.png
render shot7 1080,1920 screenshot_07_fast_sortie.png
render shot8 1080,1920 screenshot_08_victory_rewards.png

echo "Exported Play Store creatives to ${OUT}"
