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
  Set-Content $gradle $g -Encoding utf8
}
$verLine = (Select-String -Path $gradle -Pattern 'versionCode|versionName').Line -join ' / '
Write-Host "버전: $verLine"

# [3] 의존성
Step "npm install (필요 시)"
if(-not (Test-Path (Join-Path $root 'app/node_modules'))){
  Push-Location (Join-Path $root 'app'); npm install; Pop-Location
} else { Write-Host "node_modules 존재 — 건너뜀" }

# [4] 웹 자산 → 앱 번들 소스 재생성 (app/www 는 git 제외)
Step "www 재생성 (prototype + assets)"
Copy-Item (Join-Path $root 'prototype.html') (Join-Path $root 'app/www/index.html') -Force
$wwwAssets = Join-Path $root 'app/www/assets'
# robocopy /MIR: 원본 assets 를 www/assets 로 미러(불필요분 정리). 종료코드 <8 은 정상.
robocopy (Join-Path $root 'assets') $wwwAssets /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if($LASTEXITCODE -ge 8){ throw "assets 동기화 실패(robocopy $LASTEXITCODE)" } else { $global:LASTEXITCODE = 0 }
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
