"""事前hintなしのROM行クリップを全使用kernel・全左位置で画素照合する。"""
import hashlib,json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from verify_sa1_left_hints import execute


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    pointers=set()
    for asset in range(44):
        if asset in (6,7,8,37):continue
        for width in range(64,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=0x7f0000+block+1+i*10
                height=rom[entry]
                desc=struct.unpack_from('<H',rom,entry+1)[0]
                for parity in (0,1):
                    offset=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                    for y in range(height):
                        p=offset+y*11
                        assert rom[p]==0xa9 and rom[p+7]==0x22
                        pointers.add(int.from_bytes(rom[p+8:p+11],'little'))
    cases=0
    for pointer in sorted(pointers):
        assert pointer&65535,'hash sentinel cannot equal a valid row pointer'
        p=physical(pointer);code=rom[p:p+rom[p-2]];extent=rom[p-1]
        for cur in range(-extent+1,0):
            start=0;initial=0
            for i in range(0,len(code),3):
                op=code[i]
                if op==0x6b:start=i;break
                value=struct.unpack_from('<H',code,i+1)[0]
                if op==0xa9:initial=value
                if op==0x9d:
                    if value+cur+1>=0:break
                    start=i+3
            background=bytearray((i*71+0xa5)&255 for i in range(512))
            full=background.copy();partial=background.copy()
            execute(code,0,0,full,128+cur)
            execute(code,start,initial,partial,128+cur)
            assert full[128:256]==partial[128:256],(hex(pointer),cur,start)
            cases+=1
    result={'kernels':len(pointers),'clippedRowsVerified':cases,'romSha256':hashlib.sha256(rom).hexdigest()}
    (BUILD/'left_scan_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
