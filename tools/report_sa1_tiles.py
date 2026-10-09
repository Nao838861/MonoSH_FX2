"""同一のゲーム進行で細分化DMAの損益を保存する。"""
import hashlib,json,shutil,zipfile
from build_sa1_game import BUILD,ROOT

def main():
    dest=ROOT/'game/sa1/v001/results/20261010_tiles';dest.mkdir(parents=True,exist_ok=True)
    traces=[];summaries={}
    for scene in ('bands','tiles'):
        source=BUILD/scene;s=json.loads((source/'summary.json').read_text())
        assert s['presents']==470 and s['pixelMatchedPresents']>=125
        summaries[scene]=s;traces.append((source/'packet_trace.bin').read_bytes())
        shutil.copy2(source/'summary.json',dest/(scene+'.json'))
    assert traces[0]==traces[1],'comparison used different draw packets'
    (dest/'packet_trace.bin').write_bytes(traces[0])
    with zipfile.ZipFile(dest/'pixel_evidence.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for scene in summaries:
            for p in sorted((BUILD/scene).glob('present*.bin')):z.write(p,scene+'/'+p.name)
            z.write(BUILD/scene/'test.lua',scene+'/test.lua')
    text='''# 変更タイルの個別転送は既定へ採用しない

同じ471回分の描画packet（背景位置も含む）がbyte単位で一致する二方式を、完成470枚まで比較した。素材・物量・ゲーム更新の内容を変更していない。両方式とも125枚の完成FBと転送後VRAMが参照画像に一致した。

|方式|470枚までのfield数|SA-1平均ms|SA-1最大ms|平均PPU転送bytes（初期化除外）|
|---|---:|---:|---:|---:|
'''
    for scene,s in summaries.items():
        jobs=s['sa1Jobs'][3:];p=s['presentationTimes'][3:]
        text+=f'|{scene}|{s["fields"]}|{sum(j["totalSa1Ms"] for j in jobs)/len(jobs):.3f}|{max(j["totalSa1Ms"] for j in jobs):.3f}|{sum(j["dmaBytes"] for j in p)/len(p):.1f}|\n'
    text+='''
tiles方式は32bit×24行の変更bitmapを使う。descriptor設定より安い3tile以下の隙間はまとめ、二つのPPU面へ必要なrunを転送する。消去もrun単位とした。転送量は減るが、bitmap生成・走査と細かい消去の設定が増え、全体では遅い。既定はbands方式のままとし、比較実装は`--tile-dma`に分離する。

再現:

```powershell
python tools/build_sa1_game.py --tile-dma
python tools/test_sa1_game.py --frames 1800 --presents 470 --scenario tiles
python tools/build_sa1_game.py
python tools/test_sa1_game.py --frames 1800 --presents 470 --scenario bands
python tools/report_sa1_tiles.py
```

60fpsは引き続き未達。次は画像を先行して用意する構成を試す。
'''
    (dest/'report.md').write_text(text,encoding='utf-8')
    print(hashlib.sha256(traces[0]).hexdigest())

if __name__=='__main__':main()
