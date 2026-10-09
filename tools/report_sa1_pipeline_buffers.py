"""余白・退避領域・三画像保持・まとめ転送の検証結果を保存する。"""
import json, shutil, zipfile
from build_sa1_game import BUILD, ROOT


def main():
    dest = ROOT/'game/sa1/v001/results/20261010_pipeline_buffers'
    dest.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((BUILD/'manifest.json').read_text())
    rows = []
    with zipfile.ZipFile(dest/'pixel_evidence.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for scene in ('fastdma', 'bossfastdma'):
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
    for scene in ('padded', 'largecache', 'bosslarge', 'triplebw2', 'tripledma2'):
        source = BUILD/scene/'summary.json'
        if source.exists():
            shutil.copy2(source, dest/(scene+'.json'))
    report = '''# 画像保持と転送ループの改善途中

60fpsは未達。公開ROMは更新しない。原画・縮小寸法・物量・通常クロックを維持する。

|場面|実field数|完成画像数|FB/VRAM一致枚数|表示間隔field数:回数（初期2枚除外）|
|---|---:|---:|---:|---|
'''+ '\n'.join(rows)+'''

`--padded-pipeline`は512px幅へ描いて中央256pxの変更領域だけを取り出す。草の端の描画は最大約13msから約1.7msになったが、中央画像のコピーと転送待ちに平均約4.7ms加わり、600fieldで464枚に留まった。既定に採用しない。

`--large-edge-cache`は256px幅への直接描画を維持し、行ごとの切り詰め処理をROMへ移す。I-RAM workerは0200..02c2の195B、変換用32Bは02e0、画面端の退避領域は0300..06ffの1024B、行コードは0700..07ef。退避・復元のDMA排他をchunkごとにまとめる。この版は道中600field/491枚・126枚一致、ボス1200field/946枚・133枚一致。

`--triple-bw`はBW40/41/42の三面に順番に直接描く。描画前の消去には三世代分の変更を合成するが、PPU転送は二世代分だけにする。二種類の領域を同一にすると余分な転送が増える。初回の履歴は明示初期化する。metadataと地面表は五枠のまま保持する。

`--fast-dma`は転送全体のbytes・descriptor数・DRAM refresh分を含む保守的予算が残り非表示時間へ収まる場合に、descriptorごとのPPU垂直カウンタ確認を省く。収まらない場合は従来の32B単位分割へ戻す。各画像の残りbytesをmetadataへ保持し、部分転送後にも更新する。独立した全画素のFB/VRAM照合、OAM世代、表示順、非表示期間内終了を検査する。上表はこの経路と三面保持・1024B退避を同時に使った同一ROMでの結果。

道中の表示間隔2fieldは6回まで減った。ボスでは50回と3fieldが1回残る。道中600fieldとボス1200fieldは固定時間で論理進行が異なるため、以前の版との厳密な同一packet速度比ではない。平均描画時間だけで達成扱いしない。

再現:

```powershell
python tools/build_sa1_game.py --pipeline --pipeline-direct --pipeline-irq --pipeline-depth 5 --redraw-all --merge-dma --large-edge-cache --triple-bw --fast-dma
python tools/test_sa1_game.py --frames 600 --scenario fastdma
python tools/test_sa1_game.py --frames 1200 --scenario bossfastdma
python tools/report_sa1_pipeline_buffers.py
```

次は画面端の行コード切り詰めと、SA-1のDMA待ちに重なる時間を削る。ボスのCPU処理時間には地面表の再利用待ちが含まれるので、CPUの純粋な演算時間と区別する。
'''
    (dest/'report.md').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    main()
