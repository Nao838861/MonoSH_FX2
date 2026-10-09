"""透過形状だけをnativeコード化し、色データを分離して全寸法のコードを共有する。"""
import json
import struct
import numpy as np
from sa1_patterns import dimensions
from sa1_prescaled import address

def build(variants,dest,helper=0,estimate=False,game=False,hybrid=False):
    rom=bytearray(0x1000000 if estimate else 0x800000);cursor=0x20000;index=bytearray(65536);used=44*512;pool={};rowcache={};kernels=set();maxcode=0;data_set=set();lists_set=set();data_prefix={};substring_saved=0
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        while True:
            boundary=0x8000 if cursor<0x400000 else 0x10000
            if cursor%boundary+len(raw)>boundary:cursor=(cursor+boundary-1)//boundary*boundary
            blocked=next(((a,b) for a,b in ((0x400000,0x440000),(0x591300,0x600000)) if game and cursor<b and cursor+len(raw)>a),None)
            if blocked:cursor=blocked[1]
            else:break
        if not estimate and cursor+len(raw)>0x7f0000:raise ValueError(f'shared kernel ROM exhausted at {cursor:x}')
        a=cursor if estimate else address(cursor);rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);pool[raw]=a
        return a
    def color_alloc(raw):
        nonlocal substring_saved
        if raw in pool:return pool[raw]
        if len(raw)>=8:
            for pos,end in data_prefix.get(raw[:8],[]):
                if pos+len(raw)<=end and rom[pos:pos+len(raw)]==raw:
                    a=pos if estimate else address(pos);pool[raw]=a;substring_saved+=len(raw);return a
        a=alloc(raw);start=cursor-len(raw)
        for pos in range(start,cursor-7,2):
            key=bytes(rom[pos:pos+8]);entries=data_prefix.setdefault(key,[])
            if len(entries)<16:entries.append((pos,cursor))
        return a
    def idx(raw):
        nonlocal used
        a=used;index[a:a+len(raw)]=raw;used+=len(raw)
        if used>65536:raise ValueError('shared kernel lookup exhausted')
        return a
    def row_entry(row,parity):
        nonlocal maxcode
        key=(row.tobytes(),parity)
        if key in rowcache:return rowcache[key]
        a=np.pad(row,(parity,(-len(row)-parity)%4))
        words=[]
        for x in range(0,len(a),4):
            val=sum(int(c)<<(i*4) for i,c in enumerate(a[x:x+4]))
            if val:
                mask=sum((0 if (val>>(i*4))&15 else 15)<<(i*4) for i in range(4))
                words.append((x//2,mask,val))
        origin=words[0][0] if words else 0;code=bytearray();data=bytearray();i=0;accumulator=None
        while i<len(words):
            off,mask,val=words[i];off-=origin
            if hybrid and not mask and val%0x1111==0:
                if accumulator!=val:code+=b'\xa9'+struct.pack('<H',val)
                code+=b'\x9d'+struct.pack('<H',off)
                accumulator=val;i+=1;continue
            accumulator=None
            last=i+1
            if not mask:
                while last<len(words) and words[last][1]==0 and words[last][0]==words[last-1][0]+2 and not(hybrid and words[last][2]%0x1111==0):last+=1
            if last-i>=(12 if hybrid else 4):
                count=(last-i)*2
                code+=b'\xa9'+struct.pack('<H',off)+b'\x85\x80\xa9'+struct.pack('<H',count)+b'\x22'+helper.to_bytes(3,'little')
                data+=b''.join(struct.pack('<H',w[2]) for w in words[i:last])
                i=last;continue
            data+=struct.pack('<H',val)
            if mask:
                code+=b'\xbd'+struct.pack('<H',off)+b'\x29'+struct.pack('<H',mask)+b'\x85\x6c\xb7\x60\x05\x6c\x9d'+struct.pack('<H',off)+b'\xc8\xc8'
            else:code+=b'\xb7\x60\x9d'+struct.pack('<H',off)+b'\xc8\xc8'
            i+=1
        data=bytes(data)
        code+=b'\x6b';maxcode=max(maxcode,len(code));kernels.add(bytes(code));data_set.add(data)
        assert len(code)<=0x5f0,'edge kernel does not fit IRAM'
        desc=alloc(struct.pack('<H',len(code))+code).to_bytes(3,'little')+color_alloc(data).to_bytes(3,'little')+bytes([origin])
        rowcache[key]=alloc(desc)
        return rowcache[key]
    patterns=dimensions()
    for asset,sizes in sorted(patterns.items()):
        for w in sorted({w for w,h in sizes},reverse=True):
            entries=[]
            source_descriptor=None
            if game:
                ah=variants[(asset,0)][1].shape[0]
                heights=[h for ww,h in sizes if ww==w]
                source_y=sorted({int(y) for h in heights for y in np.concatenate((np.arange(h)*(ah*256//h),ah*256-1-np.arange(h)*(ah*256//h)))>>8})
                source_map=bytearray([255]*ah)
                for n,y in enumerate(source_y):source_map[y]=n
                map_address=alloc(source_map)
                source_descriptor=bytearray()
                for phase in range(3 if (asset,1) in variants else 1):
                    pix=variants[(asset,phase)][1];ah,aw=pix.shape
                    u=np.arange(w)*(aw*256//w)
                    for hflip in (False,True):
                        source=pix[:,(aw*256-1-u if hflip else u)>>8]
                        for parity in range(2):
                            rows=b''.join(row_entry(source[y],parity).to_bytes(3,'little') for y in source_y)
                            lists_set.add(rows)
                            header=map_address.to_bytes(3,'little')+alloc(rows).to_bytes(3,'little')
                            source_descriptor+=alloc(header).to_bytes(3,'little')
                descriptor_offset=idx(source_descriptor)
            for h in sorted(h for ww,h in sizes if ww==w):
                if game:
                    entries.append(bytes([h])+struct.pack('<HH',descriptor_offset,ah*256//h))
                    continue
                descriptors=bytearray()
                for phase in range(3 if (asset,1) in variants else 1):
                    pix=variants[(asset,phase)][1];ah,aw=pix.shape
                    u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
                    for hflip in (False,True):
                        source=pix[:,(aw*256-1-u if hflip else u)>>8]
                        for parity in range(2):
                            rows=b''.join(row_entry(source[int(y)],parity).to_bytes(3,'little') for y in np.concatenate((v,ah*256-1-v))>>8)
                            lists_set.add(rows)
                            descriptors+=alloc(rows).to_bytes(3,'little')
                entries.append(bytes([h])+struct.pack('<H',idx(descriptors)))
            struct.pack_into('<H',index,asset*512+w*2,idx(bytes([len(entries)])+b''.join(entries)))
    rom[0x7f0000:0x800000]=index
    summary={'geometryPatterns':sum(map(len,patterns.values())),'allGamePatterns':True,'cachedRows':len(rowcache),'sharedCodeKernels':len(kernels),'sharedCodeBytes':sum(map(len,kernels)),'colorDataBytes':sum(map(len,data_set)),'rowListsBytes':sum(map(len,lists_set)),'substringSavedBytes':substring_saved,'maxKernelBytes':maxcode,'payloadEnd':cursor,'lookupBytes':used,'romBytes':len(rom),'estimateOnly':estimate}
    (dest/'shared_kernels_packing.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
    return rom

if __name__=='__main__':
    from build_sa1_probe import assets,BUILD
    BUILD.mkdir(parents=True,exist_ok=True);build(assets(),BUILD,estimate=True)
