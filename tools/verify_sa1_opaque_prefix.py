"""実ROMから全対象のspan・safe hintをたどり、全境界の再開命令を検査する。"""
import hashlib,json,struct
from collections import Counter
from build_sa1_game import BUILD
from sa1_left_hints import physical
from sa1_patterns import dimensions
from sa1_opaque_prefix import decode_hint
from analyze_sa1_opaque_spans import spans
from analyze_sa1_opaque_capacity import boundaries
from verify_sa1_native_fragments import execute


def verify():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();manifest=json.loads((BUILD/'manifest.json').read_text())
    packing=json.loads((BUILD/'opaque_prefix_packing.json').read_text());patterns=dimensions()
    assert manifest['opaquePrefix'] and hashlib.sha256(rom).hexdigest()==manifest['romSha256']
    begin=packing['spanIndexBegin'];end=packing['spanIndexEnd'];span_count=0
    for asset in (39,40,41):
        for width in range(64,129):
            block=struct.unpack_from('<H',rom,0x7f0000+begin+(asset-39)*130+(width-64)*2)[0]
            heights=sorted(h for w,h in patterns[asset] if w==width)
            assert bool(block)==bool(heights)
            if not block:continue
            assert begin<=block<end and rom[0x7f0000+block]==len(heights)
            for i,height in enumerate(heights):
                p=0x7f0000+block+1+i*3;assert rom[p]==height
                ptr=struct.unpack_from('<H',rom,p+1)[0];assert begin<=ptr and ptr+height*2<=end
                expected=bytes(v for row in spans(asset,width,height,0,1) for v in (row[0] if row else (0,0)))
                assert rom[0x7f0000+ptr:0x7f0000+ptr+height*2]==expected
                span_count+=1
    kernels=set();rows=0
    for width,height in sorted(patterns[40]):
        if not 49<=width<=79:continue
        block=struct.unpack_from('<H',rom,0x7f0000+40*512+width*2)[0]
        entry=next(block+1+i*10 for i in range(rom[0x7f0000+block]) if rom[0x7f0000+block+1+i*10]==height)
        descriptor=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0]
        for parity in (0,1):
            p=0x7f0000+descriptor+parity*3;chain=physical(int.from_bytes(rom[p:p+3],'little'))
            for y in range(height):
                p=chain+y*11;assert rom[p]==0xa9 and rom[p+7]==0x22
                kernels.add(int.from_bytes(rom[p+8:p+11],'little'));rows+=1
    formats=Counter();tables={};checks=0;retained_hidden=0
    for pointer in sorted(kernels):
        code,blocks=boundaries(rom,pointer);p=physical(pointer);extent=rom[p-1];original=execute(code)
        n=extent//2+1
        if manifest.get('opaquePrefixInlineRaw'):
            hptr=p-2-n;marker=0;size=n
        else:
            hptr=physical(int.from_bytes(rom[p-5:p-2],'little'));marker=rom[hptr]
            size=1+3*((n+7)//8) if marker==128 else 1+5*((n+7)//8) if marker==129 else n
        encoded=rom[hptr:hptr+size];formats[str(marker if marker>=128 else 0)]+=1;tables[hptr]=size
        for index in range(n):
            pc=decode_hint(encoded,index);limit=index*2
            assert pc<len(code) and pc%3==0 and code[pc] in (0xa9,0xbd,0x6b)
            writes=execute(code[pc:]);visible={off:value for off,value in original.items() if off>=limit}
            assert all(writes.get(off)==value for off,value in visible.items())
            assert all(original[off]==value for off,value in writes.items())
            assert all(off<limit for off in original if off not in writes)
            assert index!=0 or pc==0
            assert index!=n-1 or pc==len(code)-1
            retained_hidden+=sum(off<limit for off in writes)
            checks+=1
    result=dict(romSha256=manifest['romSha256'],spanGeometries=span_count,spanIndexBytes=end-begin,
        targetNativeRows=rows,targetKernels=len(kernels),wordBoundaryChecks=checks,kernelFormats=dict(formats),
        uniqueHintBytes=sum(tables.values()),retainedHiddenWordsAcrossBoundaries=retained_hidden,
        nativeEntryRequiresNoExternalAccumulator=True,allOriginalPatternsRetained=True,goal60fpsAchieved=False)
    (BUILD/'opaque_prefix_verified.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':verify()
