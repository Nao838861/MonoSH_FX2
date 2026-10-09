"""実SA-1/FX2の同条件測定を日本語レポートと小さな証跡へ保存する。"""
import hashlib
import json
import shutil
import subprocess
import zipfile
from build_sa1_probe import BUILD, GAME, ROOT

def main():
    dest=GAME/'results/20261010_probe';dest.mkdir(parents=True,exist_ok=True)
    tables={}
    for mode in ('baseline','prescaled','compiled','fx2_comparison','dma_rows'):
        source=BUILD/mode/'summary.json';shutil.copy2(source,dest/f'{mode}.json')
        tables[mode]={r['name']:r for r in json.loads(source.read_text())['timings']}
    for name in ('asset_manifest.json','prescaled_packing.json','compiled_packing.json','compiled_estimate.json','prescaled_all_patterns_verified.json','dma_rows_packing.json'):
        shutil.copy2(BUILD/name,dest/name)
    env={'fx2SourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'mesenBinarySha256':hashlib.sha256((ROOT/'.cache/mesen_runtime/Mesen.exe').read_bytes()).hexdigest(),'mesen2ReferenceSourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'.cache/Mesen2',text=True).strip(),'masterClockHz':21477272,'gsuClockPercent':100,'sa1Overclock':False,'backgroundDrawing':False,'ppuTransferIncluded':False,'cpuGameLogicIncluded':False,'note':'Mesen2ソースは仕様調査用。使用バイナリと同一リビジョンであるとは主張しない。'}
    (dest/'environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(dest/'pixel_evidence.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for mode in tables:
            for p in sorted((BUILD/mode).glob('*.bin')):
                if '_expected' not in p.name:z.write(p,f'{mode}/{p.name}')
            for name in ('test.lua','emulator.log'):z.write(BUILD/mode/name,f'{mode}/{name}')
    names=['asset4_flip0','asset13_flip0','overlap','edge_bottom_right','boss_frame00060','play_frame01500']
    text='''# SA-1描画の段階検証（2026-10-10）

**60fpsは未達。現時点では描画計測ROMであり、SA-1版ゲームの完成ROMではない。**

既存の色付き4bpp PNG・共有paletteを変更せず、256x192の座標系、Q8.8の倍率計算、反転、透明、重なり、画面端を維持した。既存の録画packetと人工fixtureの55場面をSA-1とFX2で描き、各結果を独立した画素合成と全画素照合した。背景は双方とも空にした。自機OBJ、ゲーム処理、音、VRAM転送はこの純描画比較には含めない。

SA-1はI-RAMからkernelを実行し、通常のSA-1クロックでBW-RAMへ描く。S-CPUはWRAMのWAIで待機する。時間はhost実行時間ではなくMesen master clockで測る。消去はSA-1 DMAで24KiBをゼロにする別計測とした。

|場面|FX2（2半面合計、消去込み）ms|SA-1 画素単位 ms|SA-1 縮小済み4bpp読出し ms|SA-1 コンパイルド ms|SA-1 行DMA ms|
|---|---:|---:|---:|---:|---:|
'''
    for name in names:
        vals=[tables['fx2_comparison'][name]['totalMs']]+[tables[m][name]['drawMs'] for m in ('baseline','prescaled','compiled','dma_rows')]
        text+='|'+name+'|'+ '|'.join(f'{v:.3f}' for v in vals)+'|\n'
    text+='''
FX2の値は現行の4bpp/30fps ROMで二つの半面を描く実GSU時間の合計。SA-1の列は消去を除いた描画時間であるため、消去を含む総時間は各JSONのtotalMsを参照する。最大値同士だけで倍率を比較しない。

縮小済み画像の段階では、寸法・3色位相・4反転をROMに保持した。BW-RAM 256KiBへ全量を保持することはできない。倍率計算を消しても、packed nibbleの展開と画素単位の書込みが残り、この実装では速くならなかった。この結果は「事前縮小は無効」と一般化せず、画素単位のblitterが支配的と解釈する。

コンパイルド段階では、4画素を1wordとして不透明なら直書き、部分透明ならAND/ORする65816コードを生成した。画面端は必要な命令だけをI-RAMへDMAコピーして実行し、クリップを維持した。このROMがコードを生成するのは比較fixtureに必要な91寸法であり、ゲーム全寸法をコード化できたとは扱わない。全寸法・反転・横位置を単純に展開する見積りは8MiBを超える。

最重のコンパイルド描画でも約16.8ms、全面消去込みで約21.4ms。VRAM転送はさらに必要で、60fpsの合格条件を満たさない。次は同一packetが続く領域の再利用、変化した領域だけの消去・描画・転送、および全寸法を実ROM容量内に収める描画データ形式を検証する。ゲーム側の60Hz更新だけで達成とは判定しない。

追加で、同じ縮小行を共有し、8bytes以上の完全不透明区間をSA-1 DMAでコピーする方式も試した。全1,492寸法を8MiB ROM内に収め、55場面の画素一致は確認できた。ただし最大描画は約32.6msで、行・区間ごとの設定と複雑な透過の合成が重く、コンパイルドより遅かった。これは容量面での成立と、速度面での未達を分けて扱う。

再実行:

```powershell
$env:PATH='D:\\HomeBrew\\CC65\\bin;'+$env:PATH
python tools/build_4bpp.py --color
python tools/test_sa1_fx2_comparison.py
python tools/build_sa1_probe.py --mode baseline --dma-clear
python tools/test_sa1_probe.py
python tools/build_sa1_probe.py --mode prescaled --dma-clear
python tools/test_sa1_probe.py
python tools/verify_sa1_prescaled.py
python tools/build_sa1_probe.py --mode compiled --dma-clear
python tools/test_sa1_probe.py
python tools/build_sa1_probe.py --mode dma_rows --dma-clear
python tools/test_sa1_probe.py
python tools/report_sa1_probe.py
```

`pixel_evidence.zip`には各方式の55場面の生バッファ、Lua計測コード、エミュレータログを保存。環境・ROM SHAはJSONに記録。素材のhashをasset_manifest.jsonに保存した。MesenのSA-1レジスタ・BW-RAM・命令サイクル実装は https://github.com/SourMesen/Mesen2/tree/master/Core/SNES/Coprocessors/SA1 を参照した。
'''
    (dest/'report.md').write_text(text,encoding='utf-8')
    print(dest)

if __name__=='__main__':main()
