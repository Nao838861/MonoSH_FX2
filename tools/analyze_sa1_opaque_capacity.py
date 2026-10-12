"""全爆発寸法の不透明span表と、native分割境界表の容量を調べる。"""
import argparse,json,struct
from pathlib import Path
from collections import Counter
from analyze_sa1_opaque_spans import spans
from sa1_left_hints import physical
from sa1_patterns import dimensions


def boundaries(rom,pointer):
    """順方向nativeをword単位に分解する。繰り返しSTAは直前Aを継承する。"""
    p=physical(pointer);length=rom[p-2];code=rom[p:p+length]
    assert code[-1]==0x6b and (len(code)-1)%3==0
    blocks=[];begin=0;acc=0;mask=0
    for pc in range(0,len(code)-1,3):
        op=code[pc];operand=struct.unpack_from('<H',code,pc+1)[0]
        assert op in (0xa9,0xbd,0x29,0x09,0x9d)
        if op==0xa9:acc=operand;mask=0
        elif op==0xbd:mask=0xffff
        elif op==0x29:mask=operand
        elif op==0x09:acc=operand
        elif op==0x9d:
            blocks.append((operand,begin,pc+3,acc,mask));begin=pc+3
    assert begin==len(code)-1
    assert all(a[0]<b[0] for a,b in zip(blocks,blocks[1:])), 'expected forward native order'
    return code,blocks


def measure(rom):
    patterns=dimensions();raw=set();rle=set();rows=set();geometries=[];kernels={}
    for asset in (39,40,41):
        for w,h in sorted(patterns[asset]):
            if w<64:continue
            data=bytes(v for row in spans(asset,w,h,0,1) for v in (row[0] if row else (0,0)))
            assert len(data)==h*2
            encoded=bytearray();last=None;count=0
            for y in range(h):
                pair=data[y*2:y*2+2];rows.add(pair)
                if pair==last and count<255:count+=1
                else:
                    if last is not None:encoded+=bytes((count,))+last
                    count=1;last=pair
            encoded+=bytes((count,))+last
            decoded=b''.join(bytes(encoded[i+1:i+3])*encoded[i] for i in range(0,len(encoded),3))
            assert decoded==data
            raw.add(data);rle.add(bytes(encoded));geometries.append(dict(asset=asset,width=w,height=h,raw=len(data),rle=len(encoded)))
        # 後方の爆発用。右端逆順を避ける幅49..79で両x位相を列挙する。
        for w,h in sorted(patterns[asset]):
            if not 49<=w<=79:continue
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            entries=[block+1+i*10 for i in range(rom[0x7f0000+block])]
            entry=next(e for e in entries if rom[0x7f0000+e]==h)
            descriptor=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0]
            for parity in range(2):
                q=0x7f0000+descriptor+parity*3;chain=physical(int.from_bytes(rom[q:q+3],'little'))
                for y in range(h):
                    pointer=int.from_bytes(rom[chain+y*11+8:chain+y*11+11],'little')
                    if pointer not in kernels:kernels[pointer]=boundaries(rom,pointer)
    hints=set();with_acc=set();starts=set();instruction_hist=Counter()
    for code,blocks in kernels.values():
        end=blocks[-1][0]+2 if blocks else 0
        # Prefixはhidden word直前でRTL。Suffixは次のwordのbeginへ進み、初期Aを与える。
        stop=bytes(next((begin for off,begin,after,a,m in blocks if off>=limit),len(code)-1) for limit in range(0,end+1,2))
        values=b''.join(struct.pack('<H',next((a for off,begin,after,a,m in reversed(blocks) if off<limit),0)) for limit in range(0,end+1,2))
        hints.add(stop);with_acc.add(stop+values)
        from analyze_sa1_hint_compression import compress
        starts.add(compress(bytes(v//3 for v in stop)))
        for off,begin,after,a,m in blocks:instruction_hist[(after-begin)//3]+=1
    return dict(geometries=geometries,spanRows=len(rows),uniqueRawTables=len(raw),uniqueRleTables=len(rle),
        spanRawBytes=sum(map(len,raw)),spanRleBytes=sum(map(len,rle)),
        forwardKernels49to79=len(kernels),prefixBoundaryBytes=sum(map(len,hints)),
        prefixBoundaryCompressedBytes=sum(map(len,starts)),prefixBoundaryAndAccumulatorBytes=sum(map(len,with_acc)),
        nativeInstructionsPerWord=dict(sorted(instruction_hist.items())),
        selectorBytesExcluded=True,allRequiredGeometryPatternsEnumerated=True,gameIntegrated=False,goal60fpsAchieved=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('rom',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=measure(args.rom.read_bytes());args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='geometries'})
