"""録画と目視照合した服の画素と、脚間・輪郭外の透明を独立に検査する。"""
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'game/v001/assets'
# 32×48版で以前は透明だった、背中・ズボンの代表画素。
# 画像全体の穴埋めでは脚の間も埋まるため、透明の対照も固定する。
OPAQUE={9:[(14,17),(12,26),(12,27),(20,31),(23,32),(20,37)],
        28:[(12,15),(17,25),(18,28),(21,33),(7,37)],
        29:[(9,16),(22,26),(19,30),(22,33),(20,35),(20,39)],
        30:[(17,24),(11,26),(20,27),(17,31),(10,36),(16,40)],
        17:[(17,34),(18,34),(16,38),(13,40),(13,41)]}

def verify():
    checked=0
    for asset,points in OPAQUE.items():
        im=Image.open(ASSETS/'obj_color'/f'{asset:02d}.png')
        assert im.size==(32,48) and im.info['transparency']==0
        for point in points:
            assert im.getpixel(point)!=0,('服が透明になった',asset,point)
            checked+=1
    native=Image.open(ASSETS/'player_recording/pose00.png').convert('RGBA')
    gaps=[(18,42),(18,48),(2,25),(1,1)]
    for point in gaps:
        assert native.getpixel(point)[3]==0,('脚間・輪郭外が埋まった',point)
    meta=json.loads((ASSETS/'player_recording/source.json').read_text(encoding='utf-8'))
    expected={0:[36,61],1:[30,58],2:[26,60],3:[26,62],10:[30,59],11:[28,59],12:[32,58],13:[32,58]}
    assert {r['pose']:r['nativeSize'] for r in meta['captures']}==expected
    return {'protectedGarmentPixels':checked,'transparentControlPixels':len(gaps),
            'unchangedPoseBounds':8,'errors':0}

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
