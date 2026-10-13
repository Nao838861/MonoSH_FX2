"""草の9行目をBG2へ移す案の色・反転共有・必要CHR容量を元画像で検査する。"""
import hashlib,json
from pathlib import Path
import numpy as np
from sa1_native_far import canonical

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'game/sa1/v001/results/20261013_long_audit'


def keys(pixels):
    return {canonical(pixels[:,x:x+8])[0]for x in range(0,512,8)}


def main():
    raw=(ROOT/'build/game_v001/assets4/background4.bin').read_bytes()
    far=np.zeros((16,512),np.uint8);far[:14]=np.frombuffer(raw[:14*512],np.uint8).reshape(14,512)
    near=np.zeros_like(far);near[:9]=np.frombuffer(raw[32768:32768+9*512],np.uint8).reshape(9,512)
    original_far=keys(far[:8])|keys(far[8:]);original_near=keys(near[:8])|keys(near[8:])
    assert len(original_far)==64 and len(original_near)==62
    assert np.array_equal(near[:,:256],near[:,256:][:,::-1])
    rows=[]
    for delta in range(512):
        shifted=near[8,(np.arange(512)+delta)&511]
        merged=far.copy();merged[13]=np.where(shifted!=0,shifted,far[13])
        # 元farに9行目のnearを通常の透明合成した結果と同じ。
        assert np.array_equal(merged[13][shifted!=0],shifted[shifted!=0])
        assert np.array_equal(merged[13][shifted==0],far[13][shifted==0])
        far_count=len(keys(merged[:8])|keys(merged[8:]))
        remaining_near=len(keys(near[:8]))
        rows.append(dict(relativeScroll=delta,farTiles=far_count,remainingNearTiles=remaining_near,
            combinedChrBytes=(far_count+remaining_near)*32,
            savedChrBytes=(len(original_far)+len(original_near)-far_count-remaining_near)*32))
    result=dict(sourceSha256=hashlib.sha256(raw).hexdigest(),originalFarTiles=len(original_far),
        originalNearTiles=len(original_near),nearFirstEightRowsTiles=len(keys(near[:8])),
        transparentPixelsInNinthRow=int((near[8]==0).sum()),
        nearNinthRowColors=np.unique(near[8]).tolist(),maximumColorsPerNearTile=max(len(np.unique(near[y:y+8,x:x+8]))for y in (0,8)for x in range(0,512,8)),
        farHalfPeriod256Matches=bool(np.array_equal(far[:,:256],far[:,256:])),
        nearHalfPeriod256Matches=bool(np.array_equal(near[:,:256],near[:,256:])),
        relativeScrollCases=len(rows),worstAdditionalChrBytes=-min(x['savedChrBytes']for x in rows),
        rows=rows,sourceOnly=True,gameIntegrated=False,goal60fpsAchieved=False,
        decision='単純な最下段移動では自機二面分の896Bを空けられない。反転共有の崩れと12透明画素を無視した試作は導入しない。')
    assert result['transparentPixelsInNinthRow']==12 and result['maximumColorsPerNearTile']==7
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'near_row8_capacity.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items()if k!='rows'},indent=2))


if __name__=='__main__':main()
