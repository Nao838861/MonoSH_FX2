"""実占有maskで一世代前/二世代前との和集合の費用差だけを調べる。"""
import json,struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'
SCENARIO='movestress_detinput_captureburst_deadline_full192_tracepalette_tracebounds_tracedeadline'


def estimate(mask):
    # tm_flushと同じ48記述子上限・隙間拡張。先頭32tileは従来どおり非対象。
    gap=1
    while True:
        runs=[]
        for tile in range(32,768):
            if not mask[tile//8]>>(tile%8)&1:continue
            begin=tile*32;end=begin+32
            if runs and begin-runs[-1][1]<gap:runs[-1][1]=end
            else:runs.append([begin,end])
        if len(runs)<=48:break
        gap+=64
    lengths=[b-a for a,b in runs]
    return dict(bytes=sum(lengths),descriptors=len(runs),mergeGap=gap,
        estimatedCost=sum(n+n//32+n//128+57 for n in lengths))


def main():
    data=(BUILD/SCENARIO/'mask_bounds_trace.bin').read_bytes();assert len(data)%194==0
    masks=[]
    for i in range(len(data)//194):
        r=data[i*194:(i+1)*194];assert struct.unpack_from('<H',r)[0]==i+1
        masks.append(r[2:98])
    rows=[]
    for i in range(2,len(masks)):
        one=estimate(bytes(a|b for a,b in zip(masks[i],masks[i-1])))
        two=estimate(bytes(a|b for a,b in zip(masks[i],masks[i-2])))
        rows.append(dict(generation=i+1,frontUnion=one,backUnion=two,
            savedBytes=two['bytes']-one['bytes'],savedCost=two['estimatedCost']-one['estimatedCost']))
    burst=[x for x in rows if 530<=x['generation']<=570]
    indexed={x['generation']:x for x in rows};verified=set()
    trace=BUILD/SCENARIO/'transfer_deadline.jsonl'
    for line in trace.read_text().splitlines():
        e=json.loads(line)
        if e['event']=='pipe_setup_transfer' and e['cursor']==0 and e['generation'] in indexed:
            expected=indexed[e['generation']]['backUnion']
            assert e['remaining']==expected['bytes'] and e['descriptors']//6==expected['descriptors'],e
            verified.add(e['generation'])
    assert len(verified)>=50
    result=dict(sourceScenario=SCENARIO,sourceOnly=True,gameIntegrated=False,goal60fpsAchieved=False,
        note='前面一括更新が常に可能だと仮定した転送集合だけの比較。追加準備費、VRAM所有権、途中転送時の履歴は含めず、速度改善とは扱わない。',
        burstMeanSavedBytes=sum(x['savedBytes'] for x in burst)/len(burst),
        burstMeanSavedCost=sum(x['savedCost'] for x in burst)/len(burst),rows=rows)
    result['backUnionComparedToActualDescriptorGenerations']=len(verified)
    p=BUILD/'fixed_front_mask_probe.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print({k:v for k,v in result.items() if k!='rows'})
    print([x for x in rows if x['generation'] in (543,544,546,547,549)])


if __name__=='__main__':main()
