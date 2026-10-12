"""逆順native行の右clip開始位置と、寸法別の行recordを保持する。"""
import json,struct
from sa1_left_hints import physical
from sa1_prescaled import address

SELECTOR=0x5f6fe0


def build(rom,dest,minimum_width,inline=False):
    if inline:
        widths=set();entries=0;kernels=set()
        for asset in (40,41):
            for width in range(minimum_width,256):
                block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
                if not block:continue
                widths.add(width)
                for i in range(rom[0x7f0000+block]):
                    entry=block+1+i*10;h=rom[0x7f0000+entry];entries+=1
                    desc=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0]
                    for parity in range(2):
                        chain=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                        for y in range(h):
                            ptr=int.from_bytes(rom[chain+y*11+8:chain+y*11+11],'little');kernels.add(ptr)
                            p=physical(ptr);hint=physical(int.from_bytes(rom[p-5:p-2],'little'))
                            code=rom[p:p+rom[p-2]];stores=[];begin=0
                            for pc in range(0,len(code)-1,3):
                                if code[pc]==0x9d:
                                    assert code[begin] in (0xa9,0xbd)
                                    stores.append((struct.unpack_from('<H',code,pc+1)[0],begin));begin=pc+3
                            assert all(a[0]>b[0] for a,b in zip(stores,stores[1:]))
                            expected=bytes(next((pc for off,pc in stores if off<limit),len(code)-1) for limit in range(0,rom[p-1]+1,2))
                            assert rom[hint:hint+len(expected)]==expected
        info=dict(assets=[40,41],widths=sorted(widths),geometryEntries=entries,kernels=len(kernels),
            payloadBytes=0,ranges=[],inlineHints=True,originalNativeRowsReplaced=True,allOriginalGeometryPatternsRetained=True)
        (dest/'reverse_explosions_packing.json').write_text(json.dumps(info,indent=2)+'\n')
        return rom
    end=json.loads((dest/'left_hints_packing.json').read_text())['payloadEnd']
    ranges=[(0x5f7080,0x5f8000),(0x5f9200,0x5fc000)]
    tail=(max(end,0x7eb000)+31)&~31
    if tail<0x7f0000:ranges.append((tail,0x7f0000))
    assert not any(rom[SELECTOR:0x5f7080])
    for a,b in ranges:assert not any(rom[a:b]),f'reverse row data overlaps occupied ROM {a:x}..{b:x}'
    cursors=[a for a,b in ranges];pool={};entries=[];widths=set();kernels=set()
    def alloc(raw):
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        for i,(a,b) in enumerate(ranges):
            p=cursors[i]
            if p+len(raw)<=b:
                rom[p:p+len(raw)]=raw;cursors[i]+=len(raw);pool[raw]=address(p);return pool[raw]
        raise ValueError(f'reverse explosion metadata exhausted: {cursors}')
    for asset in (40,41):
        for width in range(minimum_width,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
            if not block:continue
            widths.add(width)
            for i in range(rom[0x7f0000+block]):
                entry=block+1+i*10;h=rom[0x7f0000+entry]
                desc=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0];maps=[]
                for parity in range(2):
                    chain=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                    rows=bytearray()
                    for y in range(h):
                        q=chain+y*11;assert rom[q]==0xa9 and rom[q+7]==0x22
                        origin=struct.unpack_from('<H',rom,q+1)[0]-y*128
                        ptr=int.from_bytes(rom[q+8:q+11],'little');p=physical(ptr)
                        length=rom[p-2];extent=rom[p-1];code=rom[p:p+length]
                        assert code[-1]==0x6b and len(code)<=255
                        stores=[];begin=0
                        for pc in range(0,len(code)-1,3):
                            if code[pc]==0x9d:
                                assert code[begin] in (0xa9,0xbd), 'right clip entry requires its own accumulator load'
                                stores.append((struct.unpack_from('<H',code,pc+1)[0],begin));begin=pc+3
                        assert all(a[0]>b[0] for a,b in zip(stores,stores[1:])), 'native row is not reversed'
                        hint=bytes(next((pc for off,pc in stores if off<limit),len(code)-1) for limit in range(0,extent+1,2))
                        rows+=ptr.to_bytes(3,'little')+alloc(hint).to_bytes(3,'little')+bytes((origin,extent))
                        kernels.add(ptr)
                    maps.append(alloc(rows))
                entries.append(struct.pack('<H',entry)+b''.join(p.to_bytes(3,'little') for p in maps))
    selector=struct.pack('<H',len(entries))+b''.join(entries)
    assert len(selector)<=0xa0
    rom[SELECTOR:SELECTOR+len(selector)]=selector
    info=dict(assets=[40,41],widths=sorted(widths),geometryEntries=len(entries),kernels=len(kernels),
        payloadBytes=sum(c-a for c,(a,b) in zip(cursors,ranges))+len(selector),
        ranges=[dict(begin=a,end=b,used=c-a) for c,(a,b) in zip(cursors,ranges)],
        originalNativeRowsReplaced=True,allOriginalGeometryPatternsRetained=True)
    (dest/'reverse_explosions_packing.json').write_text(json.dumps(info,indent=2)+'\n')
    return rom
