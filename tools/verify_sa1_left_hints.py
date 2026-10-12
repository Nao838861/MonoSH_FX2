"""途中命令からの実行結果を元の全行コード＋クリップと全位置で照合する。"""
import hashlib,json,re,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical,inline_records


def execute(code,start,initial,buffer,origin):
    a=initial
    for i in range(start,len(code),3):
        op=code[i]
        if op==0x6b:return
        v=struct.unpack_from('<H',code,i+1)[0]
        if op==0xa9:a=v
        elif op==0xbd:a=struct.unpack_from('<H',buffer,origin+v)[0]
        elif op==0x29:a&=v
        elif op==0x09:a|=v
        elif op==0x9d:struct.pack_into('<H',buffer,origin+v,a)
        else:raise AssertionError(hex(op))
    raise AssertionError('missing RTL')


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    target=int(re.search(r'\$([0-9a-f]+)',(BUILD/'left_hints.inc').read_text())[1],16)
    packing=json.loads((BUILD/'left_hints_packing.json').read_text())
    slots=packing.get('hashSlots',2048)
    entry_bytes=packing.get('hintBytesPerEntry',3)
    table=rom[physical(target):physical(target)+slots*6]
    kernels=cases=0
    entries=inline_records(rom,packing) if packing.get('inlineHeaders') else [(int.from_bytes(table[slot*6:slot*6+3],'little'),int.from_bytes(table[slot*6+3:slot*6+6],'little'),slot) for slot in range(slots)]
    symbolic_cases=0
    if packing.get('indexedInitialValues'):
        from verify_sa1_native_fragments import execute as symbolic_execute
    for record in entries:
        ptr,hint=record[:2]
        if not ptr:continue
        kernels+=1
        if packing.get('inlineHeaders'):
            assert int.from_bytes(rom[physical(ptr)-5:physical(ptr)-2],'little')==hint
        else:
            slot=record[2]
            h=((ptr&65535)>>1 ^ ((ptr>>16)<<3))&(slots-1)
            for _ in range(slots):
                if int.from_bytes(table[h*6:h*6+3],'little')==ptr:break
                assert table[h*6:h*6+3]!=bytes(3),'hash stopped at empty slot'
                h=(h+1)&(slots-1)
            assert h==slot
        p=physical(ptr);code=rom[p:p+rom[p-2]];extent=rom[p-1]
        if packing.get('indexedInitialValues'):symbolic_full=symbolic_execute(code)
        for cur in range(-extent+1,0):
            base=physical(hint);index=-cur//2
            if packing.get('indexedInitialValues'):
                data=base+index*2;start=rom[data]
                value_ptr=physical(packing['initialValueTable'])+rom[data+1]*2
                assert rom[data+1]<packing['initialValueCount']
                initial=struct.unpack_from('<H',rom,value_ptr)[0]
            elif packing.get('compressed') and rom[base]==128:
                from analyze_sa1_hint_compression import DELTAS
                data=base+1+(index//8)*3;bits=rom[data+1]|rom[data+2]<<8
                start=(rom[data]+sum(DELTAS[bits>>(j*2)&3] for j in range(index%8)))*3
            else:
                data=base+index*entry_bytes
                start=rom[data]*3
            if packing.get('indexedInitialValues'):
                assert start%3==0 and start<len(code)
            elif entry_bytes==3:initial=struct.unpack_from('<H',rom,data+1)[0]
            else:
                initial=0
                if code[start]==0x9d:
                    previous=start-3
                    while code[previous]!=0xa9:
                        previous-=3
                        assert previous>=0
                    initial=struct.unpack_from('<H',code,previous+1)[0]
            background=bytearray((i*71+0xa5)&255 for i in range(512))
            full=background.copy();partial=background.copy()
            execute(code,0,0,full,128+cur)
            execute(code,start,initial,partial,128+cur)
            assert full[128:256]==partial[128:256],(hex(ptr),cur,start)
            if packing.get('indexedInitialValues'):
                symbolic_partial=symbolic_execute(code[start:],initial)
                for off in symbolic_full.keys()|symbolic_partial.keys():
                    visible=65535 if cur+off>=0 else 0xff00 if cur+off==-1 else 0
                    if not visible:continue
                    a=symbolic_full.get(off,(off,65535,0));b=symbolic_partial.get(off,(off,65535,0))
                    assert (not a[1] or a[0]==off) and (not b[1] or b[0]==off)
                    assert a[1]&visible==b[1]&visible and a[2]&visible==b[2]&visible
                symbolic_cases+=1
            cases+=1
    result={'kernels':kernels,'clippedRowsVerified':cases,'romSha256':hashlib.sha256(rom).hexdigest()}
    if packing.get('indexedInitialValues'):result.update(symbolicClipBoundaryChecks=symbolic_cases,arbitraryFramebufferInputsVerified=True)
    (BUILD/'left_hints_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
