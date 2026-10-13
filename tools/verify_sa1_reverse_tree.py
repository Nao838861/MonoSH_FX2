"""実ROMの木4全行と、共通hintから入る可視suffixを任意下地で照合する。"""
import hashlib,json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from verify_sa1_native_fragments import execute


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    original=(BUILD/'long4000_full192_build/MonoSHSA1_4bpp_game.sfc').read_bytes()
    kernels={};geometries=rows=checks=0
    for w in range(1,256):
        a=struct.unpack_from('<H',original,0x7f0000+4*512+w*2)[0]
        b=struct.unpack_from('<H',rom,0x7f0000+4*512+w*2)[0]
        assert bool(a)==bool(b)
        if not a:continue
        assert original[0x7f0000+a]==rom[0x7f0000+b]
        for i in range(rom[0x7f0000+b]):
            ea=0x7f0000+a+1+i*10;eb=0x7f0000+b+1+i*10;h=rom[eb];geometries+=1
            da=struct.unpack_from('<H',original,ea+1)[0];db=struct.unpack_from('<H',rom,eb+1)[0]
            for parity in range(2):
                ca=physical(int.from_bytes(original[0x7f0000+da+parity*3:0x7f0000+da+parity*3+3],'little'))
                cb=physical(int.from_bytes(rom[0x7f0000+db+parity*3:0x7f0000+db+parity*3+3],'little'))
                for y in range(h):
                    x=ca+y*11;z=cb+y*11
                    assert original[x:x+8]==rom[z:z+8]
                    pa=physical(int.from_bytes(original[x+8:x+11],'little'));pb=physical(int.from_bytes(rom[z+8:z+11],'little'))
                    old=original[pa:pa+original[pa-2]];new=rom[pb:pb+rom[pb-2]]
                    assert execute(old)==execute(new)
                    kernels[pb]=new;rows+=1
    for p,code in kernels.items():
        expected=execute(code);extent=rom[p-1];idx=rom[p-3]
        table=0x5f6fe0+idx*3;hint=physical(int.from_bytes(rom[table:table+3],'little'))
        stores=[(struct.unpack_from('<H',code,pc+1)[0],pc)for pc in range(0,len(code)-1,3)if code[pc]==0x9d]
        assert all(a[0]>b[0]for a,b in zip(stores,stores[1:]))
        for limit in range(1,extent+1):
            start=0 if limit>=extent else rom[hint+(limit+1)//2]
            assert code[start]in(0xa9,0xbd,0x6b)
            partial=execute(code[start:])
            assert partial=={off:v for off,v in expected.items()if off<limit}
            for off,value in partial.items():assert value[0]in(None,off)
            checks+=1
    result=dict(romSha256=hashlib.sha256(rom).hexdigest(),referenceRomSha256=hashlib.sha256(original).hexdigest(),
        geometries=geometries,rows=rows,kernels=len(kernels),rightByteLimitsVerified=checks,
        arbitraryFramebufferInputsVerified=True,allRowOriginsRetained=True)
    assert geometries==76 and rows==9336 and len(kernels)==5751
    (BUILD/'reverse_tree_verified.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
