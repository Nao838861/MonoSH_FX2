"""保存済みpacked画像で、二世代前と同じtileを除く場合の削減上限を調べる。"""
import hashlib,json,struct,zipfile
from pathlib import Path
import numpy as np
from probe_sa1_fixed_front_mask import estimate

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261013_back_pixels'
SCENARIO='movestress_detinput_captureburst_deadline_full192_tracepalette_tracebounds_tracedeadline'


def main():
    # clone後もbuild/や未追跡cacheに依存せず、commit済みの証拠から再計算する。
    results=ROOT/'game/sa1/v001/results'
    with zipfile.ZipFile(results/'20261013_transfer_deadline/evidence.zip') as z:
        fb=z.read('road_full192/mask_bounds_frames.bin');masks=z.read('road_full192/mask_bounds_trace.bin')
    with zipfile.ZipFile(results/'20261013_flip_prepare/evidence.zip') as z:
        previous_probe=json.loads(z.read('diagnostic/fixed_front_mask_probe.json'))
    assert len(fb)%24578==0 and len(masks)%194==0
    count=len(fb)//24578;assert count<=len(masks)//194
    for i in range(count):
        assert struct.unpack_from('<H',fb,i*24578)[0]==i+1
        assert struct.unpack_from('<H',masks,i*194)[0]==i+1
    # rawは幅256pixelの4bpp packed。1tile=4B×8行、行stride=128B。
    raw=b''.join(fb[i*24578+2:(i+1)*24578]for i in range(count))
    frames=np.frombuffer(raw,dtype='<u2').reshape(count,24,8,32,2).transpose(0,1,3,2,4).reshape(count,768,16)
    rows=[];burst_differences=[]
    previous={r['generation']:r['backUnion']for r in previous_probe['rows']}
    for i in range(2,count):
        union=bytes(a|b for a,b in zip(masks[i*194+2:i*194+98],masks[(i-2)*194+2:(i-2)*194+98]))
        active=np.unpackbits(np.frombuffer(union,dtype=np.uint8),bitorder='little').astype(bool)
        active[:32]=False
        differences=frames[i]!=frames[i-2]
        changed=active&differences.any(axis=1)
        before=estimate(union);assert before==previous[i+1]
        after=estimate(np.packbits(changed,bitorder='little').tobytes())
        selected=differences[active]
        words=np.where(selected.any(axis=1),np.argmax(selected,axis=1)+1,16)
        if 530<=i+1<=570:burst_differences.extend(selected.tolist())
        rows.append(dict(generation=i+1,occupiedTiles=int(active.sum()),changedTiles=int(changed.sum()),
            backUnion=before,changedOnly=after,savedBytes=before['bytes']-after['bytes'],
            sequentialComparedWords=int(words.sum())))
    d=np.array(burst_differences,dtype=bool);remaining=np.ones(len(d),dtype=bool)
    order=[];compared=0
    for _ in range(16):
        k=max((k for k in range(16)if k not in order),key=lambda k:int((remaining&d[:,k]).sum()))
        compared+=int(remaining.sum());remaining &= ~d[:,k];order.append(k)
    burst=[r for r in rows if 530<=r['generation']<=570]
    assert len(burst)==41
    result=dict(sourceScenario=SCENARIO,sourceOnly=True,gameIntegrated=False,goal60fpsAchieved=False,
        sourceFramebuffersSha256=hashlib.sha256(fb).hexdigest(),sourceMasksSha256=hashlib.sha256(masks).hexdigest(),
        sourceFramebufferGenerations=count,burstOccupiedTiles=len(d),burstUnchangedTiles=int(remaining.sum()),
        burstChangedRatio=1-float(remaining.mean()),burstMeanSavedBytes=sum(r['savedBytes']for r in burst)/41,
        diagnosticGreedyWordOrder=order,diagnosticGreedyComparedWords=compared,rows=rows,
        note='比較命令・mask再構築の費用は含まない。元の裏面集合を独立再計算した結果と全世代一致。単発転送時間や60fpsの実証ではない。')
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items()if k!='rows'},indent=2))


if __name__=='__main__':main()
