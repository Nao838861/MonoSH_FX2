"""右端で打ち切る全行コードを、全byte境界で元コードと比較する。"""
import argparse,hashlib,json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from verify_sa1_left_hints import execute
from build_sa1_probe import assets


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--narrow',action='store_true');args=ap.parse_args()
    if args.narrow:from verify_sa1_native_fragments import execute as symbolic_execute
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
        if args.narrow:symbolic_full=symbolic_execute(code)
        for limit in range(1,min(extent,16 if args.narrow else extent)+1):
            last=0
            for i in range(0,len(code)-1,3):
                op=code[i]
                if op==0x9d:
                    offset=struct.unpack_from('<H',code,i+1)[0]
                    if offset>=limit:break
                    last=i+3
            partial=background.copy()
            reverse=next((i+3 for i in range(len(code)-4,-1,-3)
                          if code[i]==0x9d and struct.unpack_from('<H',code,i+1)[0]<limit),0)
            assert reverse==last,(hex(pointer),limit,'reverse prefix')
            execute(code[:last]+b'\x6b',0,0,partial,128)
            partial[128+limit]=background[128+limit]
            assert partial[128:128+limit]==expected[128:128+limit],(hex(pointer),limit)
            assert partial[128+limit:]==background[128+limit:],(hex(pointer),limit,'outside')
            if args.narrow:
                symbolic_partial=symbolic_execute(code[:last]+b'\x6b')
                for off in symbolic_full.keys()|symbolic_partial.keys():
                    visible=65535 if off+1<limit else 255 if off<limit else 0
                    if not visible:continue
                    a=symbolic_full.get(off,(off,65535,0));b=symbolic_partial.get(off,(off,65535,0))
                    assert (not a[1]or a[0]==off)and(not b[1]or b[0]==off)
                    assert a[1]&visible==b[1]&visible and a[2]&visible==b[2]&visible,(hex(pointer),limit,off)
            cases+=1
    result={'kernels':len(pointers),'rightByteLimitsVerified':cases,'romSha256':hashlib.sha256(rom).hexdigest()}
    if args.narrow:result.update(maximumByteLimit=16,arbitraryFramebufferInputsVerified=True)
    (BUILD/('right_narrow_verified.json'if args.narrow else 'right_clip_verified.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
