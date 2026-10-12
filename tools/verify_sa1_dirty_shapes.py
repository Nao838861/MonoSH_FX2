"""移設したdirty範囲表を、全寸法の元画像・全8縦位相から独立再計算する。"""
import hashlib,json,struct
import numpy as np
from build_sa1_game import BUILD
from build_sa1_probe import assets
from sa1_left_hints import physical


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();config=json.loads((BUILD/'manifest.json').read_text())
    assert config['rowDirtyAligned'] and config['rowDirtyExact']
    assert hashlib.sha256(rom).hexdigest()==config['romSha256']
    variants=assets();geometries=phases=small=0
    for asset in range(44):
        source=variants[asset,0][1];ah,aw=source.shape
        for w in range(256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                p=0x7f0000+block+1+i*10;h=rom[p];geometries+=1
                occupied=np.zeros((h,w),dtype=bool)
                for phase in range(3 if (asset,1) in variants else 1):
                    pix=variants[asset,phase][1];assert pix.shape==(ah,aw)
                    occupied|=pix[((np.arange(h)*(ah*256//h))>>8)[:,None],((np.arange(w)*(aw*256//w))>>8)[None,:]]!=0
                yy,xx=np.nonzero(occupied)
                bounds=bytes((int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1)) if len(xx) else bytes(4)
                assert rom[p+3:p+7]==bounds
                pointer=int.from_bytes(rom[p+7:p+10],'little')
                if w<32 or h<24:
                    assert not pointer;small+=1;continue
                assert pointer
                for phase in range(8):
                    q=physical(pointer)+phase*3;data=physical(int.from_bytes(rom[q:q+3],'little'))
                    encoded=bytearray();previous=None;run=0
                    for start in range(-phase,h,8):
                        _,xs=np.nonzero(occupied[max(0,start):min(h,start+8)])
                        pair=(int(xs.min()),int(xs.max())+1) if len(xs) else (0,0)
                        if pair==previous and run<255:run+=1
                        else:
                            if previous is not None:encoded+=bytes((*previous,run))
                            previous=pair;run=1
                    encoded+=bytes((*previous,run))
                    assert rom[data:data+len(encoded)]==encoded,(asset,w,h,phase)
                    phases+=1
    assert geometries==1492
    packing=json.loads((BUILD/'compiled_game_packing.json').read_text())
    for gap in packing.get('deferredGapRanges',[]):
        a=gap['begin'];b=gap['end'];used=gap['used']
        assert a<=a+used<=b
        assert all(a>=right or b<=left for left,right in ((0x400000,0x440000),(0x591300,0x600000),(0x7e0000,0x7eb000)))
        boundary=0x8000 if a<0x400000 else 0x10000
        assert a//boundary==(b-1)//boundary
    result=dict(romSha256=config['romSha256'],geometryPatterns=geometries,verticalPhaseTables=phases,
        smallShapesWithoutDirtyTable=small,independentSourceAlphaVerified=True,
        deferredGapBytes=packing.get('deferredGapBytes',0),reservedRomUntouched=True)
    (BUILD/'dirty_shapes_verified.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
