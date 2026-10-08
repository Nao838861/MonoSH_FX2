$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskBranch = 'experiment/4bpp-30fps-20261008'
if ((git branch --show-current) -ne $taskBranch) { throw '4bpp実験ブランチで実行してください。' }
if (git status --porcelain) { throw '未保存の変更があります。先にcommitしてください。' }
function Check-Command { if ($LASTEXITCODE -ne 0) { throw "コマンドが失敗しました: $LASTEXITCODE" } }
if (-not (Get-Command cc65 -ErrorAction SilentlyContinue)) {
    $compilerBin = 'D:\HomeBrew\CC65\bin'
    if (-not (Test-Path -LiteralPath "$compilerBin\cc65.exe")) { throw 'cc65をPATHに設定してください。' }
    $env:PATH = "$compilerBin;$env:PATH"
}
git fetch origin
Check-Command
git merge --ff-only "origin/$taskBranch"
Check-Command
git merge origin/main --no-edit
Check-Command
python -X utf8 tools/build_game.py
Check-Command
python -c "from pathlib import Path; assert Path('build/game_v001/MonoSHFX2_v001.sfc').read_bytes()==Path('releases/MonoSHFX2_v001.sfc').read_bytes(), '2bpp build differs from main release'"
Check-Command
python -X utf8 tools/build_4bpp.py --color
Check-Command
foreach ($case in ([ordered]@{'controls'=2400; 'boss'=2600; 'boss_hold'=3600; 'death'=720; 'pause'=720; 'assets'=1784; 'full'=120; 'play'=18000}).GetEnumerator()) {
    python -X utf8 tools/test_4bpp.py --scenario $case.Key --frames $case.Value
    Check-Command
    python -X utf8 tools/verify_4bpp.py $case.Key
    Check-Command
}
python -X utf8 tools/archive_4bpp.py color controls boss boss_hold death pause assets full play
Check-Command
python -X utf8 tools/build_4bpp.py
Check-Command
foreach ($case in ([ordered]@{'controls'=2400; 'boss'=2600}).GetEnumerator()) {
    python -X utf8 tools/test_4bpp.py --scenario $case.Key --frames $case.Value
    Check-Command
    python -X utf8 tools/verify_4bpp.py $case.Key
    Check-Command
}
python -X utf8 tools/archive_4bpp.py mono controls boss
Check-Command
python -X utf8 tools/build_4bpp.py --color
Check-Command
python -X utf8 tools/report_4bpp.py
Check-Command
git add game/v001/config4.json
git add game/v001/results/four_bpp_20261008
git add game/v001/RESULTS_4BPP30_20261008.md
git add releases/MonoSHFX2_4bpp30_color.sfc
git add releases/MonoSHFX2_4bpp30_mono.sfc
git add releases/4bpp30_color.json
git add releases/4bpp30_mono.json
git diff --cached --quiet
if ($LASTEXITCODE -gt 1) { throw 'stage済み差分の確認に失敗しました。' }
if ($LASTEXITCODE -eq 1) {
    git commit -m '4bpp版へmainを同期しROMと検証結果を更新'
    Check-Command
}
git push origin "HEAD:refs/heads/$taskBranch"
Check-Command
git status --branch --short
