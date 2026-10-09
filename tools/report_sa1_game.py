"""統合SA-1 ROMの検証済み中間結果を、完成扱いせず保存する。"""
import hashlib,json,shutil,zipfile
from build_sa1_game import BUILD,ROOT

def main():
    dest=ROOT/'game/sa1/v001/results/20261010_game';dest.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((BUILD/'manifest.json').read_text())
    rom=BUILD/'MonoSHSA1_4bpp_game.sfc'
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==manifest['romSha256']
    summaries={}
    for scene in ('play','boss'):
        path=BUILD/scene/'summary.json';s=json.loads(path.read_text())
        assert s['romSha256']==manifest['romSha256'],f'{scene}: stale result'
        assert s['pixelMatchedPresents']>=120
        summaries[scene]=s;shutil.copy2(path,dest/(scene+'.json'))
        for p in (BUILD/scene).glob('frame*.png'):shutil.copy2(p,dest/(scene+'_'+p.name))
    for name in ('manifest.json','compiled_game_packing.json','game.lbl'):
        shutil.copy2(BUILD/name,dest/name)
    with zipfile.ZipFile(dest/'pixel_evidence.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for scene in summaries:
            for p in sorted((BUILD/scene).glob('present*.bin')):z.write(p,f'{scene}/{p.name}')
            for name in ('test.lua','emulator.log'):z.write(BUILD/scene/name,f'{scene}/{name}')
    release=ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc';shutil.copy2(rom,release)
    shutil.copy2(BUILD/'manifest.json',ROOT/'releases/sa1_4bpp_experimental.json')
    text='''# SA-1ゲーム統合の中間測定（2026-10-10）

**60fpsは未達。動く統合ROMを保存した検証途中の記録。**

現行4bppの画像・パレット、ゲーム処理、地面と空のHDMA、既存の自機OBJ、音声を維持した独立分岐。ソフトウェア描画をSA-1へ移し、全1,492寸法の現在使用する向き・色位相・画素位相を65816コードにして8MiB ROM内に保持する。現在のゲームがソフトウェア描画で使わない左右・上下反転は、汎用比較probeと分けて明示的に検出する。自機OBJの反転は既存通り。

差分タイルだけを消去・合成し、PPUの二つのCHR面には直近2フレーム分の差分を送る。連続行の呼び出しコードで行ごとの準備を省く。描画用BW-RAMは左右に余白を持つ512px幅。キャラクタ変換DMAの最大幅256pxに合わせ、変わった行だけを別の256px幅BW-RAMへ集めてから通常のPPU DMAで送る。

独立した画像合成で完成画像を検証し、さらにその画像をSNESのタイル形式へ変換した結果と転送済みVRAMを比較した。エミュレータの通常クロックを使用。起動直後の二面初期化は全面処理のため別扱いとする。

|場面|エミュレータfield数|完成画像数|画素一致検査数|初期化後SA-1最大ms|表示field間隔の分布|
|---|---:|---:|---:|---:|---|
'''
    for scene,s in summaries.items():
        worst=max(x['totalSa1Ms'] for x in s['sa1Jobs'][3:])
        text+=f'|{scene}|{s["fields"]}|{s["presents"]}|{s["pixelMatchedPresents"]}|{worst:.3f}|{s["presentationFieldIntervals"]}|\n'
    text+='''
表示間隔0は同じfield内での複数回の完了であり、60fps達成の証拠には数えない。1以外の間隔が残っているため60fps未達と判定する。全画面の完成表示を毎field維持することが合格条件であり、平均SA-1時間やゲームロジック更新回数で代用しない。

再現手順:

```powershell
$env:PATH='D:\\HomeBrew\\CC65\\bin;'+$env:PATH
python tools/build_4bpp.py --color
python tools/build_sa1_game.py --renderer macros
python tools/test_sa1_game.py --frames 600
python tools/test_sa1_game.py --frames 1200 --scenario boss
python tools/report_sa1_game.py
```

試遊: リポジトリ直下の `play_sa1.cmd`。ROMは `releases/MonoSHSA1_4bpp_experimental.sfc`。ソース分岐は `experiment/sa1-4bpp-60fps-20261010`。元のFX2/4bpp30分岐は変更していない。

次の作業は消去・背景・連続行描画・バッファ整理の時間を分けた測定、透明な余白を除いた差分矩形、同fieldでの重複完了の抑制、重いボス場面の隠れた画素の省略。全ゲーム経路の検証は引き続き必要。
'''
    (dest/'report.md').write_text(text,encoding='utf-8')
    print(dest)

if __name__=='__main__':main()
