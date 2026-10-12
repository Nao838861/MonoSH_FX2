# 炎の左端クリップを直接参照する試験

公開版と同じ固定map設定を現行ソースで再ビルドし、そこへ `--flame-direct-hints` を追加して比較した。新基準のSHAはa9bcd2478e39f479b641ededc38d77abe4e693d2b958d1bd7b4f7ab20af603f7。公開ROMの9934d77bとはバイト単位で異なるため、過去の公開版の数字を変更前の値として流用しない。全44素材・1492寸法・色・物量・時計を保持し、公開ROMは変更しない。60fps未達。

炎31の幅64/66・全3色位相について、各native行のheader前に3バイトの表ポインタを追加。各左端位置の表は「開始命令のbyte位置1B＋必要なA初期値2B」。圧縮の解読も、繰り返しSTAから逆走してLDA即値を探す処理も不要にする。その他の草木は既存hash表を使う。補助表は重複を除いて2,490B、worker438B。allocatorが記録したバンク詰め物も補助データへ利用し、最終payloadEndは8,256,430。8MiBに収まる。

| ボスを含む1900フィールド | 表示更新 | 最大SA-1時間 | PPU全画素一致 |
|---|---:|---:|---:|
| 現行ソースの基準 | 1743 | 18.955ms | 147 |
| 直接参照有効 | 1743 | 22.393ms | 147 |
| 同配置・炎を従来経路へ戻す比較 | 1743 | 22.393ms | 147 |

有効版と同配置比較版はラベルが完全一致し、ROMの違いは分岐opcodeとchecksumの合計5バイト以内。直接参照は有効版で42 job・2151行を実行し、比較版では0行。機能が実行されたことを確認しているが、表示間隔を改善できなかった。最大時間も基準を上回るので採用しない。配置・補助表の追加による差と、炎描画経路を変える差を混同しない。

基準には2field間隔8回に加え、同じfield内の更新1回がある。有効・同配置比較はともに2field間隔7回で一致。合計表示回数だけをfpsと見なさず、1field間隔の連続性で判定する。各版の共通世代のゲームpacketも基準へ照合した。

専用fixtureは300画面で、表示後VRAM/PPU参照とRGBの全画素が一致。2寸法×7横位置×3下端位置×3色位相の全126組合せを、表示metaから確認した。上下・左右で切れる絵、完全に左へ外れる絵も含む。直接参照は131 job・7442行を通過した。軽いfixtureの表示間隔が1fieldでも、ゲーム全体の60fps達成を意味しない。

静的確認は220 kernel・768行参照・5640個の左端byte位置。2種類の下地で元native全行と部分実行の残存画素を照合し、初期Aが必要な188境界も検証した。全1492寸法・native90854行・弾158688行を旧ROMと照合、既存の草木4998 kernel・140509 clip位置も保持。移したdirty範囲表は元画像から全5992縦位相表を再計算した。

次の容量算定として、全草木の初期Aは94種類だった。3B直書き表は154698B＋kernelごとのpointer14994Bで大きい。一方、開始位置1B＋共通初期値番号1Bなら表103132B＋値辞書188B。既存hint50079B＋hash49152Bと置き換えれば、詰め物の再利用と併せて容量内に収まる可能性がある。実allocatorでの容量・実行速度は未検証で、改善結果とは扱わない。`analyze_sa1_direct_hint_capacity.py` と `direct_left_capacity.json` が根拠。

`commands.json` にPythonへ渡す引数列を保存した。各buildの後、画素検証まで完了してから次のbuildへ進む。

```text
python tools/verify_sa1_flame_direct.py
python tools/verify_sa1_reverse_explosions.py --native-only
python tools/verify_sa1_dirty_shapes.py
python tools/verify_sa1_left_hints.py
python tools/test_sa1_game.py --frames 1200 --presents 300 --scenario leftfixtureflame_direct_v2_tracepalette
python tools/test_sa1_game.py --frames 1900 --scenario bossmovestress_detinput_flamedirect_v2_long_tracepalette
python tools/analyze_sa1_direct_hint_capacity.py
python tools/report_sa1_flame_direct.py
```

ROM・labels・Lua・全summary・実VRAM/PPU設定・画面RGB・packed framebuffer・実行行ログ・静的検証・容量算定を `evidence.zip` へ収録し、SHAを `comparison.json` へ記録。試験後は現行ソースの基準ROMへ戻し、SHA一致を確認した。ユーザーが開いているMesenは操作していない。
