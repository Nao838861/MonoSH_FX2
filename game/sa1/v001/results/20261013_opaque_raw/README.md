# 省略位置の展開をなくした比較

`20261013_opaque_prefix` の行ごとの設定費用を減らすため、`--opaque-prefix-inline-raw` を追加した。安全な再開位置を1バイトの命令番号で持ち、各native行の2バイトheaderの直前に置く。ポインタ間接参照と2bit/4bit差分の展開を省く。既存の全44素材・1492寸法・色・物量・時計を維持する。60fps未達で、公開ROMへ採用しない。

raw hintは23,807バイト。初回はROM容量が足りなかったため、allocator自身が記録するバンク末尾の詰め物へdirty範囲表12,567バイトを移した。ROM内のゼロを推測して空きと見なす方式ではない。予約領域を避け、各小表のバンク跨ぎを禁止する。既存の `--reverse-records-native` も使い、右端clipの重複情報を減らす。最終payloadEndは8,310,872、IRAM workerは467バイト（圧縮版653バイトから減少）。8MiBに収まる。

| 道中800フィールド | 表示更新 | 2field間隔 | 最大SA-1時間 | PPU全画素一致 |
|---|---:|---:|---:|---:|
| raw・省略無効、同配置 | 643 | 6 | 23.184ms | 168 |
| raw・省略有効 | 643 | 6 | 26.087ms | 168 |

両者のラベルファイルとnative表配置は同一。省略は実行ログで確認したが、表示間隔を改善できなかった。前の圧縮版642更新より1回増えたことを、遮蔽自体の効果と見なさない。最大時間は有効側で悪化している。

専用fixtureは481フィールド・301表示のPPU全画素一致。対象27寸法、手前76寸法、中心8位置、上端7位置の各構成要素を通過した（全直積ではない）。各境界の再開位置は1,828カーネル・23,807境界でsymbolic検証。全寸法/native90,854行/弾158,688行と左右clipも既存検証に一致した。

移設したdirty範囲表は `verify_sa1_dirty_shapes.py` で元PNGの不透明画素から全1492寸法を再計算し、5992個の縦位相表と外接範囲が一致することを確認。小さい743寸法は従来通り追加のdirty表なし。予約ROM領域を詰め物の候補に含まないことも検査する。

初期実行では監視callbackが同じIRAMアドレスを使う別の弾workerにも反応し、まだ省略処理を選んでいない段階で停止した。省略選択から完了までの区間だけ監視するよう修正し、v5の全試験を実行した。初期失敗は速度・画素の根拠に使わず、ログを証拠へ残す。

再現には `20261013_reverse_native/commands.json` の `fiforeverseexp_v5` に次を追加する。比較版はさらに `--opaque-prefix-pass-through` を追加。

```text
--opaque-prefix --opaque-prefix-inline-raw --reverse-records-native
python tools/verify_sa1_opaque_prefix.py
python tools/verify_sa1_dirty_shapes.py
python tools/verify_sa1_reverse_explosions.py
python tools/verify_sa1_left_hints.py
python tools/test_sa1_game.py --frames 800 --scenario movestress_detinput_captureburst_opaqueprefix_v5_raw_tracepalette
python tools/test_sa1_game.py --frames 1000 --presents 300 --scenario opaquefixture_v5_raw_tracepalette
python tools/report_sa1_opaque_raw.py
```

ROM・labels・Lua・全summary・実VRAM/PPU状態・画面RGB・packed framebuffer・省略位置ログを `evidence.zip` へ保存。SHAと実行内訳は `comparison.json`。全試験後に追加flagを外したビルドは従来v5のSHA7124eab2f29ffca6904f68d1c7ee705933dd0b341bbb0082db9366468fc4a7fbに完全一致し、公開ROMのSHA9934d77b85913187be8d3ebd8315f854718eb24b08492204ce8b3288f620146cも変わっていない。
