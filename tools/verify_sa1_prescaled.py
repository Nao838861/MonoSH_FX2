"""ROMの全事前縮小データをアドレス表から読み戻し、色・反転・寸法を照合する。"""
import json
import struct
import numpy as np
from build_sa1_probe import BUILD, assets
from sa1_patterns import dimensions

def offset(a):
    bank=a>>16;low=a&65535
    if bank<0x40:return bank*32768+(low&32767)
    if 0x80<=bank<0xc0:return 0x200000+(bank-0x80)*32768+(low&32767)
    if bank>=0xc0:return 0x400000+(bank-0xc0)*65536+low
    raise ValueError(hex(a))

def main():
    rom=(BUILD/'MonoSHSA1_prescaled_probe.sfc').read_bytes();variants=assets();checks=0
    patterns=dimensions()
    for asset,sizes in patterns.items():
        for w,h in sizes:
            entry=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0];assert entry
            count=rom[0x7f0000+entry]
            records=[struct.unpack_from('<BH',rom,0x7f0001+entry+i*3) for i in range(count)]
            desc=dict(records)[h]
            for phase in range(3 if (asset,1) in variants else 1):
                pix=variants[(asset,phase)][1];ah,aw=pix.shape
                for flip in range(4):
                    pos=0x7f0000+desc+phase*12+flip*3
                    start=offset(int.from_bytes(rom[pos:pos+3],'little'))
                    raw=np.frombuffer(rom,dtype=np.uint8,count=((w+1)//2)*h,offset=start).reshape(h,(w+1)//2)
                    actual=np.stack((raw&15,raw>>4),axis=2).reshape(h,-1)[:,:w]
                    xx=np.array([((aw*256-1-x*(aw*256//w)) if flip&1 else x*(aw*256//w))//256 for x in range(w)])
                    yy=np.array([((ah*256-1-y*(ah*256//h)) if flip&2 else y*(ah*256//h))//256 for y in range(h)])
                    expected=pix[yy[:,None],xx]
                    assert np.array_equal(actual,expected),(asset,w,h,phase,flip)
                    checks+=1
    summary={'geometryPatterns':sum(map(len,patterns.values())),'bitmapVariantsVerified':checks,'allRomAddressesVerified':True}
    (BUILD/'prescaled_all_patterns_verified.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))

if __name__=='__main__':main()
