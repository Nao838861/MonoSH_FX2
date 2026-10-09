"""IRQ・保持枠・コピー削減を加えた途中結果を保存する。"""
import json, shutil, zipfile
from build_sa1_game import BUILD, ROOT


def main():
    dest = ROOT/'game/sa1/v001/results/20261010_pipeline_irq'
    dest.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((BUILD/'manifest.json').read_text())
    rows = []
    with zipfile.ZipFile(dest/'pixel_evidence.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for scene in ('overlap', 'boss'):
            source = BUILD/scene
            data = json.loads((source/'summary.json').read_text())
            assert data['romSha256'] == manifest['romSha256']
            assert data['pixelMatchedPresents'] >= 125
            assert not (source/'failure.txt').exists()
            shutil.copy2(source/'summary.json', dest/(scene+'.json'))
            shutil.copy2(source/f'frame{data["fields"]}.png', dest/(scene+'.png'))
            for path in sorted(source.glob('present*.bin')):
                archive.write(path, scene+'/'+path.name)
            archive.write(source/'test.lua', scene+'/test.lua')
            rows.append(f'|{scene}|{data["fields"]}|{data["presents"]}|{data["pixelMatchedPresents"]}|{data["presentationFieldIntervals"]}|')
    shutil.copy2(BUILD/'manifest.json', dest/'manifest.json')
    text = '''# IRQとコピー削減後の途中結果

60fpsは未達。公開ROMは更新しない。素材・色・物量は維持する。

|場面|実field数|完成画像数|FB/VRAM一致枚数|表示間隔field数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
'''+ '\n'.join(rows) + '''

五つのmetadataと地面表、二つのBW画像、二つのPPU画像を使用する。SA-1 IRQは転送用モードを設定して許可を返した後、レジスタを保存・復元して描画へ戻る。DMAを使わないnative描画は転送中も続け、描画用DMAが必要になった所で転送終了を待つ。I-RAMの変換用32Bと描画コード・退避領域は分離する。DMA criticalから戻る際もIフラグを保持し、PLPとSEIの間に転送要求が割り込む競合を防ぐ。

S-CPUの描画命令コピーはWRAMポートを入力とする逆方向DMAへ、転送descriptorコピーは通常方向のDMAへ変えた。検査のためのpacket二重コピーをゲームから除き、Lua側で対応する世代のpacketを保存する。自機OAMはmetadataから直接DMAする。BG画素だけでなくOAMの24B＋high OAMの8Bもmetadataと照合する。

消去は変更領域を使うが、`--redraw-all`では全スプライトを元の順序でnative描画する。変更領域外の最終画素も維持されることを独立合成で確認する。転送は近いdescriptorをまとめ、小さい隙間も送る。非表示時間の端で32B単位へ分割し、次fieldで残りを送る。表示済みのfieldでは切替用の予約時間を再度差し引かない。

画面端の草に最大約13msかかる例が見つかった。退避・復元する行が多く、最大256Bの退避領域に合わせると細かいchunkになる。画面端だけ行コードを切り詰める`--clip-edges`も試したが、道中600fieldでは459枚で、この方式より遅かった。転送だけtileに分ける`--transfer-tiles`も462枚で採用していない。これらは固定field数で進行量が異なる探索比較であり、厳密な同一packetの速度比ではない。

ボステストはscenarioが`boss`で始まる場合に発動するよう明示した。修正前の`bossirq`という名前の実験は通常道中であり、ボス戦の評価には使わない。本表の`boss`はステージ終了条件を90field以降に設定したボス試験である。

再現:

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 5 --redraw-all --merge-dma
python tools/test_sa1_game.py --frames 600 --scenario overlap
python tools/test_sa1_game.py --frames 1200 --scenario boss
python tools/report_sa1_pipeline_irq.py
```

次は512px幅の作業画像の中央256pxを、変更領域だけ取り出す方式を試す。以前の全中央コピーの費用と、画面端の行の退避費用を避けられるか計測する。
'''
    (dest/'report.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
