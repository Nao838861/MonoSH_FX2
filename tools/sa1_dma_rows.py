"""全縮小寸法を行単位で共有し、不透明な長い区間はSA-1 DMAで描く。"""
import json
import struct
import numpy as np
from sa1_patterns import dimensions
from sa1_prescaled import address

def build(variants,dest):
    rom=bytearray(0x800000);cursor=0x20000;index=bytearray(65536);used=44*512;pool={};rowcache={};runs=0
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        boundary=0x8000 if cursor<0x400000 else 0x10000
        if cursor%boundary+len(raw)>boundary:cursor=(cursor+boundary-1)//boundary*boundary
        if cursor+len(raw)>0x7f0000:raise ValueError('DMA row ROM exhausted')
        a=address(cursor);rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);pool[raw]=a
        return a
    def idx(raw):
        nonlocal used
        a=used;index[a:a+len(raw)]=raw;used+=len(raw)
        if used>65536:raise ValueError('DMA row lookup exhausted')
        return a
    def row_entry(row,parity):
        nonlocal runs
        key=(row.tobytes(),parity)
        if key in rowcache:return rowcache[key]
        a=np.pad(row,(parity,(-len(row)-parity)%2));packed=(a[::2]|(a[1::2]<<4)).tobytes()
        full=[(c&15)!=0 and (c>>4)!=0 for c in packed]
        long=[];x=0
        while x<len(packed):
            start=x
            if full[x]:
                while x<len(packed) and full[x]:x+=1
                if x-start>=8:long.append((start,x))
            else:x+=1
        records=[]
        def mixed(first,last):
            while first<last and packed[first]==0:first+=1
            while last>first and packed[last-1]==0:last-=1
            if first==last:return
            begin=first&~1;end=(last+1)&~1;words=bytearray()
            for xx in range(begin,end,2):
                val=sum((packed[xx+i] if first<=xx+i<last else 0)<<(8*i) for i in range(2))
                mask=sum((0 if (val>>(i*4))&15 else 15)<<(i*4) for i in range(4))
                words+=struct.pack('<HH',mask,val)
            records.append(bytes((begin,0x80|((end-begin)//2)))+alloc(words).to_bytes(3,'little')+b'\0')
        position=0
        for first,last in long:
            mixed(position,first)
            records.append(bytes((first,last-first))+alloc(packed[first:last]).to_bytes(3,'little')+b'\0')
            position=last
        mixed(position,len(packed))
        raw=struct.pack('<H',len(records))+b''.join(records)
        rowcache[key]=alloc(raw);runs+=len(records)
        return rowcache[key]
    patterns=dimensions()
    for asset,sizes in sorted(patterns.items()):
        for w in sorted({w for w,h in sizes}):
            entries=[]
            for h in sorted(h for ww,h in sizes if ww==w):
                descriptors=bytearray()
                for phase in range(3 if (asset,1) in variants else 1):
                    pix=variants[(asset,phase)][1];ah,aw=pix.shape
                    u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
                    for hflip in (False,True):
                        source=pix[:,(aw*256-1-u if hflip else u)>>8]
                        for parity in range(2):
                            rows=b''.join(row_entry(source[int(y)],parity).to_bytes(3,'little') for y in np.concatenate((v,ah*256-1-v))>>8)
                            descriptors+=alloc(rows).to_bytes(3,'little')
                entries.append(bytes([h])+struct.pack('<H',idx(descriptors)))
            struct.pack_into('<H',index,asset*512+w*2,idx(bytes([len(entries)])+b''.join(entries)))
    rom[0x7f0000:]=index
    summary={'geometryPatterns':sum(map(len,patterns.values())),'allGamePatterns':True,'cachedRows':len(rowcache),'rowRuns':runs,'payloadEnd':cursor,'lookupBytes':used,'romBytes':len(rom),'opaqueRunDmaThresholdBytes':8}
    (dest/'dma_rows_packing.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
    return rom
