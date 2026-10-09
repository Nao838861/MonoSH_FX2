"""命令によるDMA代行・ソート分担・ROM容量の途中検証を記録する。"""
import json
import shutil
import zipfile
from build_sa1_game import ROOT, BUILD
from build_sa1_probe import BUILD as PROBE


def main():
    dest = ROOT/'game/sa1/v001/results/20261010_pipeline_overlap'
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    with zipfile.ZipFile(dest/'evidence.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for scene in ('cpuedge', 'bosscpuedge', 'packetshapes', 'bosspacketshapes',
                      'prefill', 'cpufallbackall', 'fastrom', 'offloadsort12', 'bossoffloadsort12'):
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
    shutil.copy2(PROBE/'planar_feasibility.json', dest/'planar_feasibility.json')
    text = '''# 描画DMAとの並行処理の途中検証

60fps未達。公開ROMは更新しない。全て元の素材・物量・通常クロックによる。

|方式・場面|実field数|表示枚数|FB/VRAM一致枚数|表示間隔field数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
'''+'\n'.join(rows)+'''

`cpuedge`はPPUの変換DMA要求中だけ、端の退避・復元をSA-1のMVNで代行する。コード列のコピーも既存の条件付きMVNを併用し、DMA engine待ちを減らす。道中505/600・ボス1079/1200まで改善したが、道中3回・ボス29回の2field間隔が残る。

`packetshapes`は現在のpacket indexごとに寸法のlookup結果を保存し、旧矩形と描画時の検索を省く。変更した旧indexを使ってから新indexで更新する。独立参照と一致したが、表示枚数は同じ。

`prefill`は開始前に三画像を描き溜める。部分転送中は再び三画像を要求しないよう修正済み。開始が遅れる分を含め表示枚数は改善しない。`cpufallbackall`は消去・遠景コピーもPPU要求中に命令で代行するが、道中504枚で最良505枚を下回る。

`fastrom`はS-CPUの通常処理をC1 ROM bankから実行し、$420D=1を設定する。割り込み側はWRAMに維持。これは通常のFastROM動作でありクロック倍率は変更しない。S-CPUがROMを読む際のSA-1との共有が増え、道中503枚・SA-1最大23.34msで改善しない。テストは通常処理の実行bankをmanifestから選び、IRQと混同しない。

`offloadsort12`は12command以上あり、描画が既に完了した場合だけSA-1へ安定挿入ソートを渡す。ソートのコードとデータをI-RAMへ転送し、完了後にS-CPUへ戻す。job1の解放を確認してjob2を起動する。ボスでは72回分担し、全フレームで元順序と一致したが、表示枚数は1079のまま。SA-1描画時間の列には独立したソートjobの時間を含めない。最終的な表示間隔は全jobを含む実機時間で測る。

キャラクタ変換を省くため、全寸法を直接SNES planar形式へ描くコードの容量も計算した。横8位相を持つ全1,492寸法・色位相でnative codeだけで30,305,262bytes、行索引の上限約2.30MBとなり、8MiBに収まらない。これは容量評価であり実行速度の根拠ではない。直接planar化を採用するならコード共有など別の表現が必要。

最良の検証済み基本方式:

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 5 --redraw-all --merge-dma --large-edge-cache --triple-bw --fast-dma --skip-far-clear --linear-shape --cpu-code-copy --cpu-edge-copy --packet-shapes
python tools/test_sa1_game.py --frames 600 --scenario packetshapes
python tools/test_sa1_game.py --frames 1200 --scenario bosspacketshapes
```

他のflagは`--prefill-pipeline`、`--cpu-fill --cpu-far`、`--fastrom-cpu`、`--offload-sort`。各方式のROM SHAをJSONで区別する。
'''
    (dest/'report.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
