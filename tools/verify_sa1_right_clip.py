"""右端で打ち切る全行コードを、全byte境界で元コードと比較する。"""
import hashlib,json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from verify_sa1_left_hints import execute
from build_sa1_probe import assets


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    variants=assets()
    pointers=set()
    for asset in range(44):
        if asset in (6,7,8,37):continue
        for w in range(1,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=0x7f0000+block+1+i*10
                height=rom[entry]
                desc=struct.unpack_from('<H',rom,entry+1)[0]
                # 位相数は素材から取得する。
                phases=3 if (asset,1) in variants else 1
                for parity in range(phases*2):
                    offset=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                    for y in range(height):
                        p=offset+y*11
                        assert rom[p]==0xa9 and rom[p+7]==0x22
                        pointers.add(int.from_bytes(rom[p+8:p+11],'little'))
    cases=0
    for pointer in pointers:
        p=physical(pointer)
        code=rom[p:p+rom[p-2]]
        extent=rom[p-1]
        background=bytearray((i*71+0xa5)&255 for i in range(512))
        expected=background.copy()
        execute(code,0,0,expected,128)
        for limit in range(1,extent+1):
            last=0
            for i in range(0,len(code)-1,3):
                op=code[i]
                if op==0x9d:
                    offset=struct.unpack_from('<H',code,i+1)[0]
                    if offset>=limit:break
                    last=i+3
            partial=background.copy()
            execute(code[:last]+b'\x6b',0,0,partial,128)
            partial[128+limit]=background[128+limit]
            assert partial[128:128+limit]==expected[128:128+limit],(hex(pointer),limit)
            assert partial[128+limit:]==background[128+limit:],(hex(pointer),limit,'outside')
            cases+=1
    result={'kernels':len(pointers),'rightByteLimitsVerified':cases,'romSha256':hashlib.sha256(rom).hexdigest()}
    (BUILD/'right_clip_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
