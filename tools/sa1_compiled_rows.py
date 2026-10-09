"""縮小済み行の4画素を16bitで合成するコンパイルドスプライト生成器。"""
import hashlib
import json
import struct
import numpy as np
from sa1_patterns import dimensions
from sa1_prescaled import address

def build(variants,dest):
    from test_sa1_probe import jobs
    patterns={}
    for job in jobs():
        for _,_,w,h,asset,*_ in job['draws']:
            if w and h:patterns.setdefault(asset,set()).add((w,h))
    rom=bytearray(0x800000);cursor=0x20000;index=bytearray(65536);used=44*512;pool={};rowcache={}
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        boundary=0x8000 if cursor<0x400000 else 0x10000
        if cursor%boundary+len(raw)>boundary:cursor=(cursor+boundary-1)//boundary*boundary
        if cursor+len(raw)>0x7f0000:raise ValueError('compiled ROM exhausted')
        a=address(cursor);rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);pool[raw]=a
        return a
    def idx(raw):
        nonlocal used
        a=used;index[a:a+len(raw)]=raw;used+=len(raw)
        assert used<=65536
        return a
    def row_entry(row,align):
        key=(row.tobytes(),align)
        if key not in rowcache:
            code,spans=word_row(row,align)
            slots=(len(row)+align+3)//4
            raw=bytearray();position=0;i=0
            for slot in range(slots+1):
                while i<len(spans) and spans[i][0]<slot*2:
                    position+=spans[i][3];i+=1
                raw+=struct.pack('<HH',position,spans[i][2] if i<len(spans) else 0)
            rowcache[key]=alloc(code).to_bytes(3,'little')+alloc(raw).to_bytes(3,'little')
        return rowcache[key]
    for asset,sizes in sorted(patterns.items()):
        for w in sorted({w for w,h in sizes}):
            records=[]
            for h in sorted(h for ww,h in sizes if ww==w):
                descriptors=bytearray()
                for phase in range(3 if (asset,1) in variants else 1):
                    pix=variants[(asset,phase)][1];ah,aw=pix.shape
                    u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
                    for flip in range(4):
                        scaled=pix[(ah*256-1-v if flip&2 else v)>>8][:,(aw*256-1-u if flip&1 else u)>>8]
                        for align in range(4):
                            rows=b''.join(row_entry(row,align) for row in scaled)
                            descriptors+=alloc(rows).to_bytes(3,'little')
                records.append(bytes([h])+struct.pack('<H',idx(descriptors)))
            struct.pack_into('<H',index,asset*512+w*2,idx(bytes([len(records)])+b''.join(records)))
    rom[0x7f0000:]=index
    summary={'compiledGeometryPatterns':sum(map(len,patterns.values())),'allGamePatterns':False,'cachedRows':len(rowcache),'payloadEnd':cursor,'lookupBytes':used,'romBytes':len(rom)}
    (dest/'compiled_packing.json').write_text(json.dumps(summary,indent=2)+'\n')
    return rom

def word_row(row,alignment):
    pixels=np.pad(row,(alignment,(-len(row)-alignment)%4))
    code=bytearray();spans=[];accumulator=None
    for x in range(0,len(pixels),4):
        value=sum(int(c)<<(i*4) for i,c in enumerate(pixels[x:x+4]))
        if not value:continue
        mask=sum((0 if c else 15)<<(i*4) for i,c in enumerate(pixels[x:x+4]))
        offset=x//2
        begin=len(code)
        if mask:
            code+=bytes([0xbd])+struct.pack('<H',offset)+bytes([0x29])+struct.pack('<H',mask)+bytes([0x09])+struct.pack('<H',value)
            accumulator=None
        elif accumulator!=value:
            code+=bytes([0xa9])+struct.pack('<H',value);accumulator=value
        code+=bytes([0x9d])+struct.pack('<H',offset)
        spans.append((offset,mask,value,len(code)-begin))
    code.append(0x6b)
    return bytes(code),spans

def estimate(variants):
    patterns=dimensions();unique={};data={};rows=0;seen=set()
    for asset,sizes in sorted(patterns.items()):
        widths=sorted({w for w,h in sizes})
        for phase in range(3 if (asset,1) in variants else 1):
            pix=variants[(asset,phase)][1];ah,aw=pix.shape
            for w in widths:
                u=np.arange(w)*(aw*256//w)
                heights={h for ww,h in sizes if ww==w}
                used_rows=sorted({int(y) for h in heights for y in (np.arange(h)*(ah*256//h))>>8} | {int(y) for h in heights for y in (ah*256-1-np.arange(h)*(ah*256//h))>>8})
                for flip in range(2):
                    scaled=pix[used_rows][:,(aw*256-1-u if flip else u)>>8]
                    for row in scaled:
                        rows+=4
                        key=row.tobytes()
                        if key in seen:continue
                        seen.add(key)
                        for alignment in range(4):
                            code,spans=word_row(row,alignment)
                            unique[code]=len(code)
                            raw=b''.join(struct.pack('<3H',*s[:3]) for s in spans)
                            data[raw]=len(raw)
    return {'rowUses':rows,'uniqueCompiledRows':len(unique),'compiledCodeBytes':sum(unique.values()),'wordDataBytes':sum(data.values())}

if __name__=='__main__':
    from build_sa1_probe import assets, BUILD
    BUILD.mkdir(parents=True,exist_ok=True)
    s=estimate(assets());(BUILD/'compiled_estimate.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s))
