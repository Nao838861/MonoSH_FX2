"""全草木のclip初期Aを共通辞書化する場合の容量を、実ROMから算定する。"""
import hashlib,json,re,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from sa1_flame_direct import encode


def main():
    d=BUILD/'flame_currentbase_build';rom=(d/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    packing=json.loads((d/'left_hints_packing.json').read_text())
    base=physical(int(re.search(r'\$([0-9a-f]+)',(d/'left_hints.inc').read_text())[1],16))
    tables=[];values={0}
    for slot in range(packing['hashSlots']):
        p=base+slot*6;pointer=int.from_bytes(rom[p:p+3],'little')
        if not pointer:continue
        q=physical(pointer);code=rom[q:q+rom[q-2]];starts=[];begin=0
        for pc in range(0,len(code)-1,3):
            if code[pc]==0x9d:starts.append((struct.unpack_from('<H',code,pc+1)[0],begin));begin=pc+3
        raw=bytes(encode(code,starts,rom[q-1]));tables.append(raw)
        values.update(struct.unpack_from('<H',raw,i)[0] for i in range(1,len(raw),3))
    ordered=sorted(values);lookup={v:i for i,v in enumerate(ordered)};assert len(values)<=256
    indexed={bytes(v for i in range(0,len(raw),3) for v in (raw[i],lookup[struct.unpack_from('<H',raw,i+1)[0]])) for raw in tables}
    result=dict(referenceRomSha256=hashlib.sha256(rom).hexdigest(),kernels=len(tables),uniqueRawHints=len(set(tables)),
        rawHintBytes=sum(map(len,set(tables))),extraHeaderBytes=len(tables)*3,
        oldHintBytes=packing['hintBytes'],oldHashBytes=packing['hashBytes'],
        initialValues=ordered,indexedHintBytes=sum(map(len,indexed)),initialValueBytes=len(ordered)*2,
        runtimeSpeedUnmeasured=True,finalAllocatorCapacityUnproven=True)
    assert len(tables)==4998
    (BUILD/'direct_left_capacity.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
