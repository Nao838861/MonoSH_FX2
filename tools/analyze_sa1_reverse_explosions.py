"""右端から順にSTAする行コードを追加できるか、実ROMから容量を測る。"""
import json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from verify_sa1_stack_rows import execute_native


def reverse_row(code):
    words=[];value=None;mask=0
    for i in range(0,len(code)-1,3):
        op=code[i];v=struct.unpack_from('<H',code,i+1)[0]
        if op==0xa9:value=v;mask=0
        elif op==0xbd:mask=None
        elif op==0x29:mask=v
        elif op==0x09:value=v
        elif op==0x9d:
            assert value is not None and mask is not None
            words.append((v,mask,value));mask=0
        else:raise ValueError(hex(op))
    out=bytearray();hints={}
    for off,mask,value in reversed(words):
        hints[off]=len(out)
        if mask:out+=b'\xbd'+struct.pack('<H',off)+b'\x29'+struct.pack('<H',mask)+b'\x09'+struct.pack('<H',value)
        else:out+=b'\xa9'+struct.pack('<H',value)
        out+=b'\x9d'+struct.pack('<H',off)
    out+=b'\x6b'
    return bytes(out),hints


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();cases=[];verified=set();boundaries=0
    for assets,widths in (((40,41),(94,)),((40,41),(94,91)),((40,41),(91,88)),((39,40,41),(94,))):
        codes=set();hints_set=set();records=set();rows=0;entries=0;max_code=0
        for asset,width in ((a,w) for a in assets for w in widths):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=block+1+i*10;h=rom[0x7f0000+entry];entries+=1
                desc=struct.unpack_from('<H',rom,0x7f0000+entry+1)[0]
                for parity in range(2):
                    chain=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                    for y in range(h):
                        q=chain+y*11;origin=struct.unpack_from('<H',rom,q+1)[0]-y*128
                        p=physical(int.from_bytes(rom[q+8:q+11],'little'))
                        original=rom[p:p+rom[p-2]];code,hints=reverse_row(original);extent=rom[p-1]
                        if p not in verified:
                            initial=bytes((x*73+39)&255 for x in range(256))
                            expected=execute_native(original,initial)
                            for limit in range(extent+1):
                                off=next((v for v in sorted(hints,reverse=True) if v<limit),None)
                                actual=execute_native(code[hints[off]:],initial) if off is not None else bytearray(initial)
                                actual[limit]=initial[limit]
                                assert actual[:limit]==expected[:limit] and actual[limit:]==initial[limit:]
                                boundaries+=1
                            verified.add(p)
                        max_code=max(max_code,len(code));hint=bytearray()
                        for end in range(0,extent+1,2):
                            off=next((v for v in sorted(hints,reverse=True) if v<end),None)
                            hint+=bytes((hints[off],off+2)) if off is not None else bytes((len(code)-1,0))
                        codes.add(code);hints_set.add(bytes(hint));records.add((code,bytes(hint),origin,extent));rows+=1
        result=dict(assets=list(assets),widths=list(widths),entries=entries,rows=rows,
            codeBytes=sum(map(len,codes)),hintBytes=sum(map(len,hints_set)),recordBytes=len(records)*8,
            rowMapBytes=rows*2,selectorBytes=5+entries*8,maxRowCodeBytes=max_code,gameIntegrated=False)
        result['totalBytes']=sum(result[k] for k in ('codeBytes','hintBytes','recordBytes','rowMapBytes','selectorBytes'))
        cases.append(result)
    (BUILD/'reverse_explosions_capacity.json').write_text(json.dumps(cases,indent=2)+'\n')
    (BUILD/'reverse_explosions_verified.json').write_text(json.dumps(dict(kernels=len(verified),rightByteBoundaries=boundaries,gameIntegrated=False),indent=2)+'\n')
    print(cases)


if __name__=='__main__':main()
