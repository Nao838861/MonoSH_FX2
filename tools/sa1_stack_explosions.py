"""既存全寸法を残し、幅94の爆発40/41へstack描画用のROMを追加する。"""
import json,struct
from sa1_left_hints import physical
from sa1_prescaled import address
from analyze_sa1_stack_capacity import stack_row

SELECTOR=0x5f6fe0
RANGES=((0x5f7020,0x5f8000),(0x5f9200,0x5fc000),(0x7ec400,0x7f0000))


def build(rom,dest,wide=False):
    ranges=RANGES
    widths=(94,)
    if wide:
        info=json.loads((dest/'left_hints_packing.json').read_text())
        assert info.get('compressed')
        tail=(info['payloadEnd']+31)&~31
        assert tail<0x7e0000
        ranges=RANGES[:2]+((tail,0x7e0000),(0x7eb000,0x7f0000))
        widths=(94,91)
    for a,b in ((SELECTOR,0x5f8000),*ranges[1:]):
        assert not any(rom[a:b]),f'stack data overlaps occupied ROM {a:x}..{b:x}'
    cursors=[a for a,b in ranges];pool={};records=[];record_ids={};entries=[]
    def alloc(raw):
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        for i,(a,b) in enumerate(ranges):
            p=cursors[i]
            if p+len(raw)<=b:
                rom[p:p+len(raw)]=raw;cursors[i]+=len(raw)
                pool[raw]=address(p);return pool[raw]
        raise ValueError(f'stack explosion ROM exhausted; requested {len(raw)}; cursors {cursors}')
    def row_record(ptr,origin):
        p=physical(ptr);extent=rom[p-1];code=rom[p:p+rom[p-2]]
        stack,hints=stack_row(code)
        assert len(stack)<=255
        hint=bytearray()
        for end in range(0,extent+1,2):
            off=next((x for x in sorted(hints,reverse=True) if x<end),None)
            hint+=bytes((hints[off],off+2)) if off is not None else bytes((len(stack)-4,0))
        record=alloc(stack).to_bytes(3,'little')+alloc(hint).to_bytes(3,'little')+bytes((origin,extent))
        if record not in record_ids:
            record_ids[record]=len(records)*8;records.append(record)
        return record_ids[record]
    for asset,width in ((asset,width) for asset in (40,41) for width in widths):
        block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
        assert block
        for i in range(rom[0x7f0000+block]):
            entry=block+1+i*10;h=rom[0x7f0000+entry]
            desc=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0];maps=[]
            for parity in range(2):
                p=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                rows=bytearray()
                for y in range(h):
                    q=p+y*11;assert rom[q]==0xa9 and rom[q+7]==0x22
                    origin=struct.unpack_from('<H',rom,q+1)[0]-y*128
                    ptr=int.from_bytes(rom[q+8:q+11],'little')
                    rows+=struct.pack('<H',row_record(ptr,origin))
                maps.append(alloc(rows))
            entries.append(struct.pack('<H',entry)+b''.join(p.to_bytes(3,'little') for p in maps))
    table=alloc(b''.join(records))
    assert len(entries)==(6 if wide else 4), 'stack selector loop geometry count differs'
    selector=struct.pack('<H',len(entries))+table.to_bytes(3,'little')+b''.join(entries)
    assert len(selector)<=0x40
    rom[SELECTOR:SELECTOR+len(selector)]=selector
    result=dict(assets=[40,41],widths=list(widths),geometryEntries=len(entries),records=len(records),
        payloadBytes=sum(c-a for c,(a,b) in zip(cursors,ranges))+len(selector),
        ranges=[dict(begin=a,end=b,used=c-a) for c,(a,b) in zip(cursors,ranges)],
        allOtherPatternsRetained=True)
    (dest/'stack_explosions_packing.json').write_text(json.dumps(result,indent=2)+'\n')
    return rom
