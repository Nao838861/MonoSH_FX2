"""全寸法・色位相・反転をQ8.8のまま事前生成し、8MiB ROMに配置する。"""
import json
import struct
import numpy as np
from sa1_patterns import dimensions

def address(offset):
    if offset<0x200000:return ((offset>>15)<<16)|0x8000|(offset&0x7fff)
    if offset<0x400000:return ((0x80+((offset-0x200000)>>15))<<16)|0x8000|(offset&0x7fff)
    return ((0xc0+((offset-0x400000)>>16))<<16)|(offset&0xffff)

def build(variants,dest):
    rom=bytearray(0x800000)
    # $02:8000は24KiBのDMA clear sourceとして予約する。
    cursor=0x20000
    index=bytearray(65536);used=44*512
    patterns=dimensions();entries=[]
    def index_alloc(raw):
        nonlocal used
        start=used;index[start:start+len(raw)]=raw;used+=len(raw)
        if used>65536:raise ValueError('prescale lookup bank exhausted')
        return start
    def alloc(raw):
        nonlocal cursor
        boundary=0x8000 if cursor<0x400000 else 0x10000
        if cursor%boundary+len(raw)>boundary:cursor=(cursor+boundary-1)//boundary*boundary
        if cursor+len(raw)>0x7f0000:raise ValueError('prescaled 8MiB ROM exhausted')
        start=cursor;rom[start:start+len(raw)]=raw;cursor+=len(raw)
        return address(start)
    for asset,sizes in sorted(patterns.items()):
        bywidth={w:sorted(h for ww,h in sizes if ww==w) for w,h in sizes}
        for w,heights in sorted(bywidth.items()):
            records=[]
            for h in heights:
                descriptors=bytearray()
                for phase in range(3 if (asset,1) in variants else 1):
                    _,pix=variants.get((asset,phase),variants[(asset,0)])
                    ah,aw=pix.shape
                    u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
                    for flip in range(4):
                        xx=(aw*256-1-u if flip&1 else u)>>8
                        yy=(ah*256-1-v if flip&2 else v)>>8
                        scaled=pix[yy][:,xx]
                        if w&1:scaled=np.pad(scaled,((0,0),(0,1)))
                        packed=(scaled[:,::2]|(scaled[:,1::2]<<4)).tobytes()
                        a=alloc(packed);descriptors+=a.to_bytes(3,'little')
                start=index_alloc(descriptors)
                records.append(bytes([h])+struct.pack('<H',start))
                entries.append([asset,w,h])
            start=index_alloc(bytes([len(records)])+b''.join(records))
            struct.pack_into('<H',index,asset*512+w*2,start)
    rom[0x7f0000:]=index
    summary={'geometryPatterns':len(entries),'bitmapEnd':cursor,'lookupBytes':used,'romBytes':len(rom),'bwRamBytes':262144,'allPatternsIn':'ROM','allFlips':True,'allBulletPhases':True}
    (dest/'prescaled_packing.json').write_text(json.dumps(summary,indent=2)+'\n')
    return rom
