# 地上物体の爆発先頭で影が出る不具合の修正

2026年10月9日。依頼原文：「爆発も修正して。」前回の指摘は「60fps版、爆発の1パターンめに真っ黒の絵が入ってる？」。

2bpp・60fps版で、木などを破壊したときの最初の爆発画像が影になっていた。`stage.s` の爆発位相計算後に `cmp #0` を追加し、位相0で本来の爆発画像5を選ぶようにした。従来は `cmp #4` の比較結果が残り、位相0でも画像38（自機の影）を選んでいた。4bpp版で修正済みの同じ条件分岐を、2bpp版でも修正した。

六段階の画像選択は、修正前の `38,39,40,41,40,39` から `5,39,40,41,40,39` になる。通常敵とボスは既に別経路で正しく画像5を選ぶ。爆発原画を差し替える必要はなかった。

## 爆発の表示検証

`tools/verify_stage_explosions.py` は、実ゲームの地上物体描画の入口に爆発状態を設定し、実際に選ばれた描画命令を検査する。遮蔽する別物体だけを取り除き、選択済みの命令をそのままGSU・PPUへ通す。単に爆発画像を直接指定する試験ではない。

修正前ROMに新しい期待値の検査を実行すると、先頭で `wrong explosion asset 38 expected 5` と失敗した。修正前の状態を記録するbaseline試験と修正後の試験を、それぞれ六位相×カラー／モノクロの12場面で実行した。

修正後は全12場面で正しい画像を選び、589,824個のFB画素と2,172個の不透明PPU画素が独立した原画縮小・透明合成・色の計算と一致した。[修正前後の比較](results/stage_explosion_20261009/comparison.png)。白黒では、修正前の黒い塊から白い爆発の輪郭を持つ絵になった。

直前に更新した地面四色もdisplay720フィールドで再検証し、三カメラの最終PPU全画素とFX・OBJが一致した。全ROMの原画・地面HDMA・音源を含むoffset0x20000以降は変更前と全byte一致。CPUソースの変更は条件判定の一命令だけ。

通常入力6,000フィールド（約99.8秒）でボス到達・撃破・次周を確認した。5,998画像を提示し、全5,997間隔が1フィールド、60.0988fps・表示遅延0回。道中5,369、ボス稼働343、撃破演出102、撃破後179の同一区分内間隔もすべて1フィールド。CPU最大14.052ms、GSU最大14.745ms。20場面の全FBとOBJ照合も通過した。

変更前ROMは `38d2fccd3f125c413d019b83073294e5eb47beb2dcda1ebbce8371b002ce560d`、更新ROMは `003f820676f1acb5d3ee189c26f4c15cb265f1d2e2542f370486d7c17aef4a4b`。集計と生ログは同所の `summary.json` と `natural/performance.json`。今回のMesen・入力条件の観測であり、任意の入力や実機での保証ではない。

## 再現手順

プロジェクトのルートで実行する。`--output` には新しい出力先を指定する。

```powershell
python -X utf8 tools/build_game.py
python -X utf8 tools/verify_stage_explosions.py --output build/game_v001/explosion_local_check
python -X utf8 tools/test_game.py --scenario display --frames 720 --timeout 120
python -X utf8 tools/profile_boss.py --frames 6000 --timeout 240 --output boss_profile_explosioncheck --allow-unreleased
python -X utf8 tools/report_color_60hz.py build/game_v001/boss_profile_explosioncheck --require-60hz
```

自己評価：黒い爆発の原因だった画像選択を実ゲームの経路で再現し、先頭だけを正しい爆発へ戻せた。モノクロの不透明な黒と透明色も区別して確認した。
