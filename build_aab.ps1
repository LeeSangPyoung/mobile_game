<#
  build_aab.ps1 — 손가락삼국지 서명 AAB 원클릭 빌드 (Windows PowerShell)
  사용:
    ./build_aab.ps1                # 현재 버전 그대로 빌드
    ./build_aab.ps1 -BumpVersion   # versionCode +1, versionName 패치 +1 후 빌드
  전제: [0] 키스토어(app/android/keystore.properties + upload-keystore.jks) 배치, JDK23 / Node22 / Android SDK. 자세한 건 BUILD.md.
#>
param([switch]$BumpVersion)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

function Step($m){ Write-Host "`n=== $m ===" -ForegroundColor Cyan }

# [1] 키스토어 확인
Step "키스토어 확인"
$ksProps = Join-Path $root 'app/android/keystore.properties'
$ksJks   = Join-Path $root 'app/android/upload-keystore.jks'
if(-not (Test-Path $ksProps) -or -not (Test-Path $ksJks)){
  throw "서명 키스토어 없음. BUILD.md [0] 참고 — app/android/ 에 keystore.properties + upload-keystore.jks 를 넣으세요."
}

# [2] 버전 상향(옵션)
$gradle = Join-Path $root 'app/android/app/build.gradle'
if($BumpVersion){
  Step "버전 상향"
  $g = Get-Content $gradle -Raw
  $g = [regex]::Replace($g, 'versionCode\s+(\d+)', { param($m) 'versionCode ' + ([int]$m.Groups[1].Value + 1) })
  $g = [regex]::Replace($g, 'versionName\s+"(\d+)\.(\d+)\.(\d+)"', { param($m) 'versionName "' + $m.Groups[1].Value + '.' + $m.Groups[2].Value + '.' + ([int]$m.Groups[3].Value + 1) + '"' })
  # -Encoding utf8 은 Windows PowerShell 5.1 에서 BOM 을 붙인다.
  # gradle 이 그 BOM 을 글자로 읽어 빌드가 첫 줄에서 죽는다. BOM 없이 쓴다.
  [IO.File]::WriteAllText($gradle, $g, (New-Object Text.UTF8Encoding $false))
}
$verLine = (Select-String -Path $gradle -Pattern 'versionCode|versionName').Line -join ' / '
Write-Host "버전: $verLine"

# [3] 의존성
Step "npm install (필요 시)"
if(-not (Test-Path (Join-Path $root 'app/node_modules'))){
  Push-Location (Join-Path $root 'app'); npm install; Pop-Location
} else { Write-Host "node_modules 존재 — 건너뜀" }

# [4] 웹 자산 → 앱 번들 소스 재생성 (app/www 는 git 제외)
#   예전엔 robocopy /MIR 로 assets 를 통째로 미러했는데, assets 가 2.1GB 로 자라
#   AAB 가 509MB 가 됐다(Play 기본 설치 한도 200MB). 지금은 tools/build_www.py 가
#   (a) 참조 0건 폴더와 발주 원본(*_source.*)을 빼고
#   (b) 일기토 컷을 1280x1024 -> 640x512 로 줄이고 (화면엔 403px 로 그려진다)
#   (c) PNG/JPG 를 WEBP 로 바꾸면서 index.html 의 경로까지 같이 고친다.
#   원본 assets/ 와 prototype.html 은 건드리지 않는다 — 사본만 손본다.
Step "www 재생성 (prototype + assets 최적화)"
Copy-Item (Join-Path $root 'prototype.html') (Join-Path $root 'app/www/index.html') -Force
if(Test-Path (Join-Path $root 'duel_v2.html')){
  Copy-Item (Join-Path $root 'duel_v2.html') (Join-Path $root 'app/www/duel_v2.html') -Force
}
Push-Location $root
python tools/build_www.py
if($LASTEXITCODE -ne 0){ Pop-Location; throw "www 최적화 실패(build_www.py $LASTEXITCODE)" }
Pop-Location
if(Test-Path (Join-Path $root 'img')){ Copy-Item (Join-Path $root 'img') (Join-Path $root 'app/www/img') -Recurse -Force -ErrorAction SilentlyContinue }

# [5] capacitor 동기화
Step "cap sync android"
Push-Location (Join-Path $root 'app'); npx --no-install cap sync android; Pop-Location

# [6] 서명 릴리스 번들
Step "bundleRelease (서명 AAB)"
Push-Location (Join-Path $root 'app/android')
& .\gradlew.bat :app:bundleRelease --no-daemon
Pop-Location

# [7] 결과
$aab = Join-Path $root 'app/android/app/build/outputs/bundle/release/app-release.aab'
if(Test-Path $aab){
  Step "완료"
  $sz = [math]::Round((Get-Item $aab).Length/1MB,1)
  Write-Host "AAB: $aab ($sz MB)" -ForegroundColor Green
  Write-Host "서명 지문 확인:"
  try { keytool -printcert -jarfile $aab | Select-String 'SHA256' } catch { Write-Host "(keytool 미발견 — 수동 확인)" }
  Write-Host "`n→ Play Console 에 이 AAB 업로드. 지문이 A1:A0:69:73:CC:3F:8B:90:...:2B:18:4B:37 와 일치해야 함." -ForegroundColor Yellow
} else { throw "AAB 생성 실패 — 위 gradle 로그 확인" }
