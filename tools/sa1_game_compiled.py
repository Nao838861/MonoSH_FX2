"""現行ゲームで使用する全寸法・色位相・横2画素位相を直接65816コードにする。"""
import json,struct
import numpy as np
from sa1_patterns import dimensions
from sa1_prescaled import address

def build(variants,dest,macros=False):
    rom=bytearray(0x800000);cursor=0x20000;index=bytearray(65536);used=44*512;pool={};rowcache={};codes=set();maximum=0
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        while True:
            boundary=0x8000 if cursor<0x400000 else 0x10000
            if cursor%boundary+len(raw)>boundary:cursor=(cursor+boundary-1)//boundary*boundary
            block=next(((a,b) for a,b in ((0x400000,0x440000),(0x591300,0x600000)) if cursor<b and cursor+len(raw)>a),None)
            if block:cursor=block[1]
            else:break
        if cursor+len(raw)>0x7f0000:raise ValueError(f'compiled game ROM exhausted: {cursor:x}')
        a=address(cursor);rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);pool[raw]=a
        return a
    def idx(raw):
        nonlocal used
        a=used;index[a:a+len(raw)]=raw;used+=len(raw)
        if used>65536:raise ValueError('compiled index exhausted')
        return a
    def row_entry(row,parity):
        nonlocal maximum
        key=row.tobytes(),parity
        if key in rowcache:return rowcache[key]
        pixels=np.pad(row,(parity,(-len(row)-parity)%4));words=[]
        for x in range(0,len(pixels),4):
            val=sum(int(c)<<(n*4) for n,c in enumerate(pixels[x:x+4]))
            if val:
                mask=sum((0 if c else 15)<<(n*4) for n,c in enumerate(pixels[x:x+4]))
                words.append((x//2,mask,val))
        origin=words[0][0] if words else 0;code=bytearray();acc=None
        for offset,mask,value in words:
            offset-=origin
            if mask:
                code+=b'\xbd'+struct.pack('<H',offset)+b'\x29'+struct.pack('<H',mask)+b'\x09'+struct.pack('<H',value)
                acc=None
            elif acc!=value:
                code+=b'\xa9'+struct.pack('<H',value);acc=value
            code+=b'\x9d'+struct.pack('<H',offset)
        code+=b'\x6b';maximum=max(maximum,len(code));assert len(code)<=0x1f0
        codes.add(bytes(code))
        end=words[-1][0]+2 if words else 0
        packed=pixels[::2]|pixels[1::2]<<4
        best=(0,0);start=0
        for n in range(len(packed)+1):
            if n<len(packed) and packed[n]&15 and packed[n]>>4:continue
            if n-start>best[1]-best[0]:best=(start,n)
            start=n+1
        header=bytes((len(code),end-origin)) if macros else bytes((max(0,best[0]-origin),max(0,best[1]-origin)))
        ptr=alloc(header+code)+2
        rowcache[key]=ptr.to_bytes(3,'little')+bytes([len(code),origin,end])
        return rowcache[key]
    patterns=dimensions()
    for asset,sizes in sorted(patterns.items()):
        for w in sorted({w for w,h in sizes},reverse=True):
            pix=variants[asset,0][1];ah,aw=pix.shape;heights=sorted(h for ww,h in sizes if ww==w)
            entries=bytearray()
            for h in heights:
                ys=(np.arange(h)*(ah*256//h))>>8;desc=bytearray()
                for phase in range(3 if (asset,1) in variants else 1):
                    pix=variants[asset,phase][1];source=pix[:,(np.arange(w)*(aw*256//w))>>8]
                    for parity in range(2):
                        if macros:
                            program=bytearray()
                            for dy,y in enumerate(ys):
                                row=row_entry(source[int(y)],parity)
                                program+=b'\xa9'+struct.pack('<H',dy*128+row[4])+b'\x18\x65\xf8\xaa\x22'+row[:3]
                            program+=b'\x6b';rows=alloc(program)
                        else:rows=alloc(b''.join(row_entry(source[int(y)],parity) for y in ys))
                        desc+=rows.to_bytes(3,'little')
                entries+=bytes([h])+struct.pack('<H',idx(desc))
                if macros:
                    occupied=np.zeros((h,w),dtype=bool)
                    for phase in range(3 if (asset,1) in variants else 1):
                        pixels=variants[asset,phase][1]
                        occupied|=pixels[ys[:,None],((np.arange(w)*(aw*256//w))>>8)[None,:]]!=0
                    yy,xx=np.nonzero(occupied)
                    bounds=(int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1) if len(xx) else (0,0,0,0)
                    entries+=bytes(bounds)
            struct.pack_into('<H',index,asset*512+w*2,idx(bytes([len(heights)])+entries))
    rom[0x7f0000:]=index
    info={'geometryPatterns':sum(map(len,patterns.values())),'currentGamePatterns':True,'horizontalFlipSupported':False,'verticalFlipSupported':False,'pixelParities':2,'rowDescriptorBytes':11 if macros else 6,'nativeRowCallChains':macros,'uniqueRows':len(rowcache),'uniqueCodeKernels':len(codes),'nativeCodeBytes':sum(map(len,codes)),'maxKernelBytes':maximum,'payloadEnd':cursor,'lookupBytes':used}
    (dest/'compiled_game_packing.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info))
    return rom

if __name__=='__main__':
    from build_sa1_probe import assets,BUILD
    build(assets(),BUILD)
