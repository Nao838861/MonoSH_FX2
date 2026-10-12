"""全炎kernel・全左clip位置を、元native行の実行結果へ照合する。"""
import hashlib,json,struct
from sa1_left_hints import physical
from build_sa1_game import BUILD
from verify_sa1_left_hints import execute


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();config=json.loads((BUILD/'manifest.json').read_text())
    assert config['flameDirectHints'] and hashlib.sha256(rom).hexdigest()==config['romSha256']
    pointers=set();geometries=rows=0
    for width in range(64,256):
        block=struct.unpack_from('<H',rom,0x7f0000+31*512+width*2)[0]
        if not block:continue
        for i in range(rom[0x7f0000+block]):
            p=0x7f0000+block+1+i*10;h=rom[p];desc=struct.unpack_from('<H',rom,p+1)[0]+0x7f0000;geometries+=1
            for phase in range(6):
                chain=physical(int.from_bytes(rom[desc+phase*3:desc+phase*3+3],'little'))
                for y in range(h):
                    q=chain+y*11;assert rom[q]==0xa9 and rom[q+7]==0x22
                    pointers.add(int.from_bytes(rom[q+8:q+11],'little'));rows+=1
    cases=sta=0;unique={}
    for pointer in sorted(pointers):
        p=physical(pointer);code=rom[p:p+rom[p-2]];extent=rom[p-1]
        hint=physical(int.from_bytes(rom[p-5:p-2],'little'));unique[hint]=(extent//2+1)*3
        for cur in range(-extent+1,0):
            data=hint+(-cur//2)*3;start=rom[data];initial=struct.unpack_from('<H',rom,data+1)[0]
            assert start<len(code) and start%3==0 and code[start] in (0xa9,0xbd,0x9d,0x6b)
            sta+=code[start]==0x9d
            for seed in (0,0xa5):
                bg=bytearray((i*71+seed)&255 for i in range(512));full=bg.copy();partial=bg.copy()
                execute(code,0,0,full,128+cur);execute(code,start,initial,partial,128+cur)
                assert full[128:256]==partial[128:256],(pointer,cur,start,seed)
            cases+=1
    result=dict(romSha256=config['romSha256'],geometries=geometries,nativeRowUses=rows,kernels=len(pointers),
        leftByteBoundaries=cases,repeatedStoreBoundaries=sta,uniqueHintBytes=sum(unique.values()),
        independentNativeExecutionVerified=True)
    assert geometries==2 and len(pointers)==220 and sta>0
    (BUILD/'flame_direct_verified.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
