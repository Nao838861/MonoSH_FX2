"""不透明spanと、Aの外部初期化なしでnative行へ再開するhintを保持する。"""
import json,struct
import numpy as np
from sa1_patterns import dimensions
from analyze_sa1_hint_compression import compress,DELTAS


def safe_hint(code,starts,extent):
    safe={};last_load=0;store_begin=0
    for pc in range(0,len(code)-1,3):
        if code[pc] in (0xa9,0xbd):last_load=pc
        if code[pc]==0x9d:
            safe[store_begin]=last_load;store_begin=pc+3
    raw=bytes(next((safe[pc]//3 for off,pc in starts if off>=limit),(len(code)-1)//3) for limit in range(0,extent+1,2))
    assert raw[0]<128 and all(a<=b for a,b in zip(raw,raw[1:]))
    choices=[raw]
    try:choices.append(compress(raw))
    except ValueError:pass
    packed=bytearray((129,))
    for start in range(0,len(raw),8):
        block=raw[start:start+8];bits=0
        for i in range(1,len(block)):
            delta=block[i]-block[i-1]
            if delta>15:break
            bits|=delta<<((i-1)*4)
        else:
            packed+=bytes((block[0],))+bits.to_bytes(4,'little')
            continue
        break
    else:choices.append(bytes(packed))
    encoded=min(choices,key=len)
    assert all(decode_hint(encoded,i)==v*3 for i,v in enumerate(raw))
    return encoded


def decode_hint(encoded,index):
    if encoded[0]==128:
        p=1+(index//8)*3;bits=int.from_bytes(encoded[p+1:p+3],'little')
        return (encoded[p]+sum(DELTAS[bits>>(i*2)&3] for i in range(index%8)))*3
    if encoded[0]==129:
        p=1+(index//8)*5;bits=int.from_bytes(encoded[p+1:p+5],'little')
        return (encoded[p]+sum(bits>>(i*4)&15 for i in range(index%8)))*3
    return encoded[index]*3


def finish(rom,dest,variants):
    packing=json.loads((dest/'compiled_game_packing.json').read_text())
    begin=packing['lookupBytes'];cursor=begin+390;pool={};blocks=[]
    assert not any(rom[0x7f0000+begin:])
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        assert cursor+len(raw)<=65536, f'opaque span lookup exhausted {cursor+len(raw)}'
        p=cursor;rom[0x7f0000+p:0x7f0000+p+len(raw)]=raw;cursor+=len(raw);pool[raw]=p
        return p
    patterns=dimensions()
    for asset in (39,40,41):
        pix=variants[asset,0][1];ah,aw=pix.shape
        for w in sorted({w for w,h in patterns[asset] if w>=64}):
            records=bytearray()
            for h in sorted(h for ww,h in patterns[asset] if ww==w):
                image=pix[(np.arange(h)*(ah*256//h))>>8][:,(np.arange(w)*(aw*256//w))>>8]!=0
                raw=bytearray()
                for row in image:
                    edges=np.diff(np.pad(row.astype(np.int8),(1,1)))
                    runs=list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
                    left,right=max(runs,key=lambda pair:pair[1]-pair[0]) if runs else (0,0)
                    assert row[left:right].all()
                    raw+=bytes((left,right))
                pointer=alloc(raw);records+=bytes((h,))+struct.pack('<H',pointer)
                blocks.append(dict(asset=asset,width=w,height=h,spanPointer=0xff0000+pointer))
            block=alloc(bytes((len(records)//3,))+records)
            struct.pack_into('<H',rom,0x7f0000+begin+(asset-39)*130+(w-64)*2,block)
    (dest/'opaque_prefix.inc').write_text(f'OPAQUE_SPAN_TABLE=${0xff0000+begin:06x}\n',encoding='utf-8')
    info=dict(targetAsset=40,targetMinimumWidth=49,targetMaximumWidth=79,spanAssets=[39,40,41],spanMinimumWidth=64,
        spanIndexBegin=begin,spanIndexEnd=cursor,spanIndexBytes=cursor-begin,spanGeometries=blocks,
        originalPatternsRetained=True,opaquePrefixInlineHeaders=True)
    (dest/'opaque_prefix_packing.json').write_text(json.dumps(info,indent=2)+'\n');print(info)
    return rom
