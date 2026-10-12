# 不透明な手前の爆発による、奥のnative描画の先頭省略

前回の専用probeで出た省略可能量を、実ゲームに組み込んで測定した。既存の44素材・1492寸法・縮小・色・当たり判定・時計・表示領域を保持する。公開ROMは変更しない。60fps未達。

`--opaque-prefix` は画面左右に収まる素材40の幅49～79だけを対象とする。描画順が後の素材39～41（幅64以上）から矩形交差面積が最大の1個を選び、その各行の最長不透明区間に隠れる先頭を省く。区間に穴があれば省略しない。各native行は直前のLDAから再開するため、Aの外部初期値に依存しない。対象外・端で切れる絵は従来経路へ戻す。

補助表の容量は、FFバンクの空きに10,221バイト、nativeの補助hintに10,807バイト。行呼び出し表を20行ずつIRAMへコピーし、JSL先だけを更新する。IRAM作業コード・表のコピー、前後関係の検索、圧縮hintの展開もゲーム内SA-1の実時間に含む。前回のホスト生成oracleとは異なる。

| 800フィールドの道中 | 表示更新 | 2フィールド間隔 | 最大SA-1時間 | PPU全画素一致 |
|---|---:|---:|---:|---:|
| v5基準（前回） | 645 | 4 | 22.779ms | 168 |
| v3同配置・即時辞退 | 644 | 5 | 23.186ms | 168 |
| v3省略有効 | 642 | 7 | 25.394ms | 168 |

同配置比較はラベルファイルが完全一致し、入り口の3バイトだけを切り替える。native表も同一。実際の省略をログに記録しており、機能が通らなかっただけという比較ではない。判定と各行の設定費が削れた描画量を上回った。現状は既定経路に採用しない。ボスを含む1,900フィールドでも146画面がPPU全画素一致したが、60fpsには届かない。詳細値は `comparison.json`。

専用fixtureでは300画面のPPU全画素が一致した。最初の通常画面を除く299画面で、対象27寸法・手前76寸法・中心8位置・上端7位置の各構成要素を通過した。全直積を検証したという意味ではない。間に弾を描き、IRAM上書き後の再ロードも検証する。raw・2bit差分・4bit差分の3形式が実際に処理された。

静的検証では76個の不透明区間を元PNGの透過から独立再計算し、1,828カーネル・23,807境界の再開位置と残る画素を検証。全1492寸法、native行90,854回、弾行158,688回も旧ROMと照合。既存の右クリップ59,519境界、左クリップ190,929境界を保持した。

初期v1は4bit差分のrank=0時に余計な差分を加算し、画面の8バイトが不一致になった。v2で修正し、v1を性能判断から除外した。修正前後のログを証拠ZIPに残す。

再現には `20261013_reverse_native/commands.json` の `fiforeverseexp_v5` に `--opaque-prefix` を追加する。比較版はさらに `--opaque-prefix-pass-through` を追加する。テストは以下。Python 3.12の同梱runtimeを使用した。

```text
python tools/verify_sa1_opaque_prefix.py
python tools/verify_sa1_reverse_explosions.py
python tools/verify_sa1_left_hints.py
python tools/test_sa1_game.py --frames 800 --scenario movestress_detinput_captureburst_opaqueprefix_v3_active_tracepalette
python tools/test_sa1_game.py --frames 1900 --scenario bossmovestress_detinput_opaqueprefix_v3_active_long_tracepalette
python tools/test_sa1_game.py --frames 1000 --presents 300 --scenario opaquefixture_v2_tracepalette
python tools/report_sa1_opaque_prefix.py
```

fixtureはv2 ROM、実プレイは同じ修正済み処理に3バイトの比較用入り口を加えたv3 ROMで実行した。ROM・ラベル・Lua・実VRAM/PPU設定・画面RGB・packed framebuffer・全計測summary・省略位置ログを `evidence.zip` に保存し、各ROMのSHAとZIPのSHAを `comparison.json` に記録した。
