"""実際のnative描画chunkについて、既存alpha帯表で退避幅を絞れる量を測る。"""
import argparse,collections,json,struct
from pathlib import Path
from sa1_left_hints import physical

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/sa1_game'


def bands(rom,asset,width,height):
    block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
    for i in range(rom[0x7f0000+block]):
        p=0x7f0000+block+1+i*10
        if rom[p]==height:break
    else:raise AssertionError((asset,width,height))
    table=physical(int.from_bytes(rom[p+7:p+10],'little'))
    ptr=physical(int.from_bytes(rom[table:table+3],'little'))
    result=[]
    while len(result)<(height+7)//8:
        left,right,count=rom[ptr:ptr+3];assert count
        result.extend([(left,right)]*count);ptr+=3
    assert len(result)==(height+7)//8
    return result


def projected_width(event,rom):
    e=event
    if e['cacheWidth']>32 or e['asset'] not in (40,41) or e['left']<0 or e['flags']&0x30 or e['width']<32 or e['height']<24:
        return e['cacheWidth']
    rows=bands(rom,e['asset'],e['width'],e['height'])
    right=max(r for l,r in rows[e['first']//8:(e['first']+e['count']+7)//8])
    width=max(0,(right+e['left']-255)//2) if right else 0
    if e['cacheWidth']<=32:width=(width+1)&~1
    assert width<=e['cacheWidth'],(e,width)
    return width


def main():
    ap=argparse.ArgumentParser();ap.add_argument('scenario');ap.add_argument('--rom',type=Path,default=BUILD/'edgeguard_base_build/MonoSHSA1_4bpp_game.sfc');args=ap.parse_args()
    rom=args.rom.read_bytes();events=[json.loads(x) for x in (BUILD/args.scenario/'edge_cache.jsonl').read_text().splitlines()]
    totals={};selected=[]
    for asset in sorted({e['asset'] for e in events}):
        es=[e for e in events if e['asset']==asset];old=sum(e['cacheBytes'] for e in es)
        new=sum(projected_width(e,rom)*e['cacheRows'] for e in es)
        totals[str(asset)]=dict(chunks=len(es),copiedBytesOneDirection=old,projectedBytesOneDirection=new,
            saveMs=sum(e['saveMs'] for e in es),restoreMs=sum(e['restoreMs'] for e in es))
    for e in events:
        width=projected_width(e,rom)
        if width<e['cacheWidth']:selected.append(dict(**e,projectedWidth=width,projectedBytes=width*e['cacheRows']))
    result=dict(scenario=args.scenario,perAsset=totals,smallerChunks=len(selected),smaller=selected,
        measuredHelperSpeed=False,goal60fpsAchieved=False)
    dest=BUILD/(args.scenario+'_analysis.json');dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='smaller'},indent=2))


if __name__=='__main__':main()
