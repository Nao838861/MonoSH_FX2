# 草木の左端を2バイト表で直接参照する試験

60fpsは未達。独立SA-1分岐で全44素材・1492寸法・色・物量・通常クロックを保持して比較した。公開ROMは変更しない。現行ソースの基準はa9bcd247、試験版は61b2a071。基準は公開ROM9934d77bとバイト単位で異なるため、今回測った基準との比較を使う。

草木0/2/3/5の幅64以上について、各native行のheader前に表ポインタ3Bを置く。境界ごとの内容は「開始命令のbyte位置1B＋初期Aの辞書番号1B」。共通辞書は94値・188Bで、CGRAMの色数とは別のpacked pixel値である。各行のhash検索と、繰り返しSTAの直前のLDA探索を除く。対象4998 kernel、重複を除いた3011表・103132B。allocatorが記録した安全なバンク詰め物11535Bも使い、payloadEnd=8319685で8MiBに収まった。補助workerは313B。

|試験|表示更新|表示間隔 field:回数|最大SA-1時間|PPU全画素一致|
|---|---:|---|---:|---:|
|基準・道中800field|647|1:640、2:4|22.002ms|168|
|直接表・道中800field|646|1:638、2:5|22.962ms|168|
|基準・ボスを含む1900field|1743|0:1、1:1731、2:8|18.955ms|147|
|直接表・ボスを含む1900field|1743|1:1733、2:7|19.036ms|147|

道中では直接表が53 job・1394行を通ったが、表示遅れが1回増えた。ボス試験では対象の草木経路を通った行が0なので、ボスの差を直接表の高速化と解釈しない。同配置の無効比較は今回行っていないため、ROM配置の影響とhelper変更の影響は分離していない。全体改善がないので採用しない。共通logic世代のpacketは道中652世代・ボス1748世代が一致した。初期2枚を除いて実表示fieldの間隔を数え、同field内の二重更新を2枚の60fps表示と扱わない。

専用fixtureは69寸法×14横中心×3上端の全2898組合せ。横中心は-40/-39/0/1/16/17/30/31/64/65/128/129/250/251、上端は-20/30/180。1600画面で実VRAM・PPU参照・paletteを含めた全画素が一致し、30175行・750 job・全4素材の直接表を通過した。初回CLIは画素照合後のcoverage集計で、fixtureに切り替わる前の通常の初期1画面までfixtureと数えてassertに失敗した。初期画面も画素一致している。その1件だけをcoverage対象から除く修正後、保存済み全metaを再検査して全2898ケースを確認した。エミュレータは再実行しておらず、初回失敗ログと修正後の検査ログを両方保存している。軽いfixtureの1field間隔はゲーム全体の達成証拠ではない。

静的検証は4998 kernel・140509左端位置で、元の全行実行と部分実行が一致。さらに各wordを元の下地の記号式として評価し、残る可視bitのmask/valueを照合して、任意の下地入力でも一致することを確認した。native全1492寸法・90854行、弾158688行、dirty全5992縦位相表も元データとの一致を確認した。

`--direct-left-hints` は既定OFF。`commands.json` にbuild引数を保存した。検証順は以下。

```text
python tools/verify_sa1_reverse_explosions.py --native-only
python tools/verify_sa1_dirty_shapes.py
python tools/verify_sa1_left_hints.py
python tools/test_sa1_game.py --frames 800 --scenario movestress_detinput_captureburst_directleft_v2_tracepalette
python tools/test_sa1_game.py --frames 2600 --presents 1600 --timeout 300 --scenario leftfixtureindexed_directleft_v2_tracepalette
python tools/test_sa1_game.py --frames 1900 --scenario bossmovestress_detinput_directleft_v2_long_tracepalette
python tools/report_sa1_direct_left.py
```

`evidence.zip` は36649593B、SHA256はfc6235cbd10bbcd617036b64f49892890a285885282902dd3b54d289f8a975a5。ROM・labels・manifest・静的結果・全summary・Lua・packet・packed framebuffer・VRAM・PPU設定・RGB・実行行ログ・CLIログを収録する。PNGは同一RGBの重複なので省く。試験後はflagを外して基準a9bcd247へ戻し、公開版9934d77bの保持も確認した。

今回の基準の最悪jobは22.002ms=描画15.038＋dirty計算3.269＋クリア2.953＋背景0.742ms。画面右端で切れる爆発41・幅94は単体7.117msだった。右端の逆順native、可視prefixコピー、IRAM行窓は既に試験済みなので、同じ案を新案として繰り返さず、過去の全画面の退行も含めて次を検討する。
