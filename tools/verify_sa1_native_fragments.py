"""native行の任意word境界でのprefix/suffix分割を実ROM命令から検証する。"""
import argparse,hashlib,json,struct
from pathlib import Path
from analyze_sa1_opaque_capacity import boundaries
from sa1_left_hints import physical
from sa1_patterns import dimensions


def execute(code,initial=0):
    """Aを(old[offset] & mask) | constantとして追跡し、入力FBを限定しない。"""
    source=None;mask=0;value=initial;writes={}
    for pc in range(0,len(code),3):
        op=code[pc]
        if op==0x6b:
            assert pc==len(code)-1
            return writes
        operand=struct.unpack_from('<H',code,pc+1)[0]
        if op==0xa9:source=None;mask=0;value=operand
        elif op==0xbd:source=operand;mask=65535;value=0
        elif op==0x29:mask&=operand;value&=operand
        elif op==0x09:value|=operand;mask&=~operand&65535
        elif op==0x9d:
            assert operand not in writes, 'a fragment rewrote a previous word'
            writes[operand]=(source if mask else None,mask,value)
        else:raise AssertionError(f'unsupported instruction {op:02x}')
    raise AssertionError('fragment did not return')


def verify(rom):
    kernels=set();rows=0;checks=0;pairs=0;acc_reused=0
    for asset in (39,40,41):
        for w,h in sorted(dimensions()[asset]):
            if not 49<=w<=79:continue
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            entry=next(block+1+i*10 for i in range(rom[0x7f0000+block]) if rom[0x7f0000+block+1+i*10]==h)
            desc=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0]
            for parity in (0,1):
                q=0x7f0000+desc+parity*3;chain=physical(int.from_bytes(rom[q:q+3],'little'))
                for y in range(h):
                    q=chain+y*11;assert rom[q]==0xa9 and rom[q+7]==0x22
                    kernels.add(int.from_bytes(rom[q+8:q+11],'little'));rows+=1
    for pointer in sorted(kernels):
        code,blocks=boundaries(rom,pointer);original=execute(code)
        assert all(result[0] in (None,off) for off,result in original.items()), 'cross-word input dependency'
        end=blocks[-1][0]+2 if blocks else 0;n=end//2+1;pairs+=n*(n+1)//2
        for limit in range(0,end+1,2):
            pc=next((begin for off,begin,after,a,m in blocks if off>=limit),len(code)-1)
            prefix=execute(code[:pc]+b'\x6b')
            assert prefix=={off:result for off,result in original.items() if off<limit}
            previous=next(((a,m) for off,begin,after,a,m in reversed(blocks) if off<limit),(0,0))
            if code[pc]==0x9d:
                assert not previous[1], 'STA entry needs a nonconstant accumulator'
                acc_reused+=1
            suffix=execute(code[pc:],previous[0])
            assert suffix=={off:result for off,result in original.items() if off>=limit}
            checks+=1
    return dict(romSha256=hashlib.sha256(rom).hexdigest(),assets=[39,40,41],minimumWidth=49,maximumWidth=79,
        nativeRows=rows,uniqueKernels=len(kernels),wordBoundaryChecks=checks,impliedIntervalPairs=pairs,
        suffixAccumulatorReuseBoundaries=acc_reused,
        symbolicFramebufferInputs=True,allPrefixSuffixCompositionsVerified=True,
        gameIntegrated=False,runtimeCostMeasured=False,goal60fpsAchieved=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('rom',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=verify(args.rom.read_bytes());args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(result)
