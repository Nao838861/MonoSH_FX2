"""背景レイヤー化と輪郭に沿うdirty範囲の途中計測を保存する。"""
import json
import zipfile
from build_sa1_game import ROOT, BUILD


def main():
    dest = ROOT/'game/sa1/v001/results/20261010_native_background'
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    scenes = ('bossbackgroundjobverified', 'backgroundadaptive',
              'backgroundfrontdelta', 'backgroundrowdelta',
              'backgroundbanddelta', 'backgroundbanddouble', 'bossbandwait')
    with zipfile.ZipFile(dest/'evidence.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for scene in scenes:
            source = BUILD/scene
            data = json.loads((source/'summary.json').read_text())
            assert data['pixelMatchedPresents'] >= 125
            assert not (source/'failure.txt').exists()
            small = {k: v for k, v in data.items() if not isinstance(v, list)}
            (dest/(scene+'.json')).write_text(json.dumps(small, indent=2)+'\n')
            for path in sorted(source.glob('present*.bin')):
                z.write(path, scene+'/'+path.name)
            for name in ('test.lua', 'summary.json', f'frame{data["fields"]}.png'):
                z.write(source/name, scene+'/'+name)
            rows.append(f'|{scene}|{data["fields"]}|{data["presents"]}|{data["pixelMatchedPresents"]}|{data["presentationFieldIntervals"]}|')
    report = '''# 背景のBG2化と転送範囲の削減

全条件での60fpsは未達。道中600fieldの一条件だけは表示開始後514枚すべて1field間隔を確認した。ボスでは30回の2field間隔が残る。公開ROMは変更しない。元の画像・物量・表示範囲・通常クロックを維持。

|構成・場面|実field数|表示枚数|画素照合枚数|表示間隔field数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
'''+ '\n'.join(rows)+'''

`--native-background`は遠景と近景をBG2の14行に合成する。SA-1は横スクロールが整数画素で変わる時だけ2KiBを更新し、地面オフセットはBG2の縦位置とTM HDMAで反映する。スプライトは従来どおりSA-1による4bppソフトウェア描画。地面399tileへの反転共有と配置変更は全2048map要素の画素一致を確認した。元PNGは編集していない。

背景の生画像はBW43:8000..BFFFの8版に保持する。record+40/+42に画像アドレス・版番号を保存する。PPUへの背景転送は640/384/1024Bの3区間で、地面CHRとmapを上書きしない。BG2 mapはC600/CE00、CHR base C000。$210Bの上位nibbleは6。channel7をTM HDMAとして有効にし、元の見える14行だけ表示する。

`--row-dirty --row-dirty-bands`は各寸法の不透明部分の横範囲を8行単位で事前保持する。画像そのものは変えず、消去・転送範囲だけを絞る。高さdescriptorは10B、RLEの追加payloadは13,860B、全payload末尾7D5979、FF索引50,977Bで8MiBに収まる。1行単位版は転送範囲がさらに狭いが、範囲計算に時間がかかる。

`backgroundbanddouble`は二面VRAMの二世代dirty方式で、道中514枚・126枚FB/VRAM/BG2/地面照合、表示間隔はすべて1field。単一世代を表示面へ直接送る`--front-delta`は大きい変更時に全面裏面転送へ戻るため悪化した。物理VRAM面ごとのdirty蓄積も先行描画の世代数が増えて悪化した。

`--wait-slots`はBWまたはmetadataの空き待ちをWAIへ変更し、共有I-RAMの連続pollを減らす。SEIで条件確認してからWAI、起床後CLIとして通知取りこぼしを防ぐ。ボス1084枚・136枚一致でも2field間隔30回が残り、達成とはしない。

起動時のrelease flag $1Eの未初期化を修正した。最初のSA-1 jobが重複して実行される場合があり、従来の初回全面描画では画素検証が検出しなかった。producerは$0188へ世代番号を常に送り、SA-1開始時に$0198へ保存する。新しい検証は実jobの番号が連続することも確認する。本表の構成は$1E明示初期化後。背景専用の$0194/$0196も初期化する。

再現例:

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 5 --redraw-all --merge-dma --large-edge-cache --triple-bw --fast-dma --linear-shape --cpu-code-copy --cpu-edge-copy --packet-shapes --native-background --row-dirty --row-dirty-bands --wait-slots
python tools/test_sa1_game.py --frames 1200 --scenario bossbandwait
```

道中の同一ROM・武器変更・左右移動・長時間の試験はまだ不足している。保存した各結果のROM hashを区別し、表の複数構成を同じROMの結果として扱わない。
'''
    (dest/'report.md').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    main()
