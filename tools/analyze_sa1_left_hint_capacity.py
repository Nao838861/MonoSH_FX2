"""既存hashの空きに爆発の左端hintを足す容量を測る。ROMは書き換えない。"""
import json,struct,re
from build_sa1_game import BUILD
from sa1_left_hints import physical
from build_sa1_probe import assets


def analyze():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();variants=assets()
    packing=json.loads((BUILD/'left_hints_packing.json').read_text())
    slots=packing['hashSlots']
    target=int(re.search(r'\$([0-9a-f]+)',(BUILD/'left_hints.inc').read_text())[1],16)
    table=rom[physical(target):physical(target)+slots*6]
    old={int.from_bytes(table[i:i+3],'little') for i in range(0,len(table),6)}-{0}
    keys=set()
    for ptr in old:
        p=physical(ptr);extent=rom[p-1];length=(extent+1)//2+1
        h=((ptr&65535)>>1 ^ ((ptr>>16)<<3))&(slots-1)
        while int.from_bytes(table[h*6:h*6+3],'little')!=ptr:h=(h+1)&(slots-1)
        hint=int.from_bytes(table[h*6+3:h*6+6],'little');q=physical(hint)
        keys.add(rom[q:q+length])
    base_bytes=sum(map(len,keys));rows=[]
    current=set(old)
    for asset in (39,40,41):
        found=set()
        for w in range(64,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=0x7f0000+block+1+i*10;h=rom[entry]
                desc=struct.unpack_from('<H',rom,entry+1)[0]
                for parity in range(6 if (asset,1) in variants else 2):
                    offset=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                    for y in range(h):
                        p=offset+y*11
                        assert rom[p]==0xa9 and rom[p+7]==0x22
                        found.add(int.from_bytes(rom[p+8:p+11],'little'))
        for ptr in found-current:
            p=physical(ptr);length=rom[p-2];extent=rom[p-1];code=rom[p:p+length]
            stores=[];begin=0
            for i in range(0,length-1,3):
                if code[i]==0x9d:
                    stores.append((struct.unpack_from('<H',code,i+1)[0],begin));begin=i+3
            encoded=bytes(next((begin for off,begin in stores if off+1>=word*2),length-1)//3 for word in range((extent+1)//2+1))
            keys.add(encoded)
        current|=found
        rows.append(dict(asset=asset,kernels=len(found),totalKernels=len(current),
                         extraHintBytes=sum(map(len,keys))-base_bytes,hashSlots=slots,
                         hashLoad=len(current)/slots,fitsHash=len(current)<slots))
    result=dict(oldKernels=len(old),oldHintBytes=base_bytes,availableProjectionBytes=0x6fde,rows=rows)
    (BUILD/'left_hint_capacity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':analyze()
