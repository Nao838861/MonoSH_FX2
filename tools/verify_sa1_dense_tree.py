"""木4の実ROMのPEA/PHAを独立解釈し、全寸法・左右全byte境界を照合する。"""
import hashlib,json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from verify_sa1_native_fragments import execute


def execute_dense(code,pc,sp):
    a=(None,0,0);out={}
    while True:
        op=code[pc];pc+=1
        if op==0x5c:
            assert code[pc:]==b'\x00\x07\x00';return out
        if op in (0xf4,0xbd,0x29,0x09):
            v=struct.unpack_from('<H',code,pc)[0];pc+=2
            if op==0xf4:out[sp-1]=(None,0,v);sp-=2
            elif op==0xbd:a=out.get(v,(v,65535,0))
            elif op==0x29:a=(a[0],a[1]&v,a[2]&v)
            else:a=(a[0],a[1]&~v&65535,a[2]|v)
        elif op==0x48:out[sp-1]=(a[0]if a[1]else None,a[1],a[2]);sp-=2
        else:raise AssertionError(hex(op))


def nonidentity(state):return {off:v for off,v in state.items()if v!=(off,65535,0)}


def verify_stack_window(extent):
    count=0
    for row in (0,128,8064,8192,16256,16384,24448,32768,40832,40960,49024,49152,57216):
        for cur in range(1-extent,128):
            limit=min(extent,128-cur)
            end=extent if cur<0 else (limit+1)//2*2
            dest=(row+cur)&65535;low=(dest+end-2)&65535;high=(low+1)&65535
            base=(high if cur<0 else low)&0xe000
            sp=0x6000+(high&8191)if cur<0 else 0x6001+(low&8191)
            minimum=(-cur)//2*2 if cur<0 else 0
            for off in range(end-2,minimum-1,-2):
                for byte in (1,0):
                    target=(dest+off+byte)&65535
                    if row<=target<row+128:
                        assert 0x6000<=sp<0x8000 and base+sp-0x6000==target,(row,cur,extent,off,sp,target)
                        count+=1
                    sp=(sp-1)&65535
    return count


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    original=(BUILD/'long4000_full192_build/MonoSHSA1_4bpp_game.sfc').read_bytes()
    kernels={};geometries=rows=right=left=0;extents=set()
    for w in range(1,256):
        a=struct.unpack_from('<H',original,0x7f0000+4*512+w*2)[0]
        b=struct.unpack_from('<H',rom,0x7f0000+4*512+w*2)[0];assert bool(a)==bool(b)
        if not a:continue
        assert original[0x7f0000+a]==rom[0x7f0000+b]
        for i in range(rom[0x7f0000+b]):
            ea=0x7f0000+a+1+i*10;eb=0x7f0000+b+1+i*10;h=rom[eb];geometries+=1
            da=struct.unpack_from('<H',original,ea+1)[0];db=struct.unpack_from('<H',rom,eb+1)[0]
            for parity in range(2):
                ca=physical(int.from_bytes(original[0x7f0000+da+parity*3:0x7f0000+da+parity*3+3],'little'))
                cb=physical(int.from_bytes(rom[0x7f0000+db+parity*3:0x7f0000+db+parity*3+3],'little'))
                for y in range(h):
                    x=ca+y*11;z=cb+y*11;assert original[x:x+8]==rom[z:z+8]
                    pa=physical(int.from_bytes(original[x+8:x+11],'little'));pb=physical(int.from_bytes(rom[z+8:z+11],'little'))
                    old=execute(original[pa:pa+original[pa-2]])
                    code=rom[pb:pb+rom[pb-2]];extent=rom[pb-1]
                    assert nonidentity(execute_dense(code,0,extent-1))==old
                    kernels[pb]=(code,old);rows+=1
    for p,(code,old)in kernels.items():
        extent=rom[p-1];table=0x5f6fe0+rom[p-3]*3
        extents.add(extent)
        hint=physical(int.from_bytes(rom[table:table+3],'little'))
        assert len(code)<=0xc0 and code[-4:]==b'\x5c\x00\x07\x00'
        for limit in range(1,extent+1):
            start=rom[hint+(limit+1)//2]
            actual=execute_dense(code,start,((limit+1)//2)*2-1)
            assert nonidentity(actual)=={off:v for off,v in old.items()if off<limit};right+=1
        for minimum in range(1,extent):
            length=rom[hint+minimum//2]
            actual=execute_dense(code[:length]+b'\x5c\x00\x07\x00',0,extent-1)
            assert nonidentity(actual)=={off:v for off,v in old.items()if off>=minimum//2*2};left+=1
    result=dict(romSha256=hashlib.sha256(rom).hexdigest(),referenceRomSha256=hashlib.sha256(original).hexdigest(),
        geometries=geometries,rows=rows,kernels=len(kernels),rightByteLimitsVerified=right,leftByteLimitsVerified=left,
        arbitraryFramebufferInputsVerified=True,allRowOriginsRetained=True,maximumKernelBytes=max(len(v[0])for v in kernels.values()),
        bwRamStackVisibleByteMappingsVerified=sum(verify_stack_window(e)for e in extents))
    assert geometries==76 and rows==9336 and len(kernels)==5751
    (BUILD/'dense_tree_verified.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
