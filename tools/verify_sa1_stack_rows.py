"""逆順stack行の全右端境界を、元のnative行と比較する。"""
import json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical
from analyze_sa1_stack_capacity import stack_row


def execute_native(code,initial):
    out=bytearray(initial);a=0
    for i in range(0,len(code)-1,3):
        op=code[i];v=struct.unpack_from('<H',code,i+1)[0]
        if op==0xa9:a=v
        elif op==0xbd:a=struct.unpack_from('<H',out,v)[0]
        elif op==0x29:a&=v
        elif op==0x09:a|=v
        elif op==0x9d:struct.pack_into('<H',out,v,a)
        else:raise ValueError(hex(op))
    return out


def execute_stack(code,pc,sp,initial):
    out=bytearray(initial);a=0
    while code[pc]!=0x5c:
        op=code[pc];pc+=1
        if op in (0xf4,0xbd,0x29,0x09,0xe9):
            v=struct.unpack_from('<H',code,pc)[0];pc+=2
            if op==0xf4:struct.pack_into('<H',out,sp-1,v);sp-=2
            elif op==0xbd:a=struct.unpack_from('<H',out,v)[0]
            elif op==0x29:a&=v
            elif op==0x09:a|=v
            else:a=(a-v)&65535
        elif op==0x48:struct.pack_into('<H',out,sp-1,a);sp-=2
        elif op==0x3b:a=sp
        elif op==0x38:pass
        elif op==0x1b:sp=a
        else:raise ValueError(hex(op))
    return out


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();ptrs=set();checked=0
    widths=json.loads((BUILD/'stack_explosions_packing.json').read_text()).get('widths',[94])
    for asset,width in ((asset,width) for asset in (40,41) for width in widths):
        block=struct.unpack_from('<H',rom,0x7f0000+asset*512+width*2)[0]
        for i in range(rom[0x7f0000+block]):
            p=0x7f0000+block+1+i*10;h=rom[p];desc=struct.unpack_from('<H',rom,p+1)[0]
            for parity in range(2):
                chain=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                for y in range(h):ptrs.add(int.from_bytes(rom[chain+y*11+8:chain+y*11+11],'little'))
    for ptr in ptrs:
        p=physical(ptr);code=rom[p:p+rom[p-2]];extent=rom[p-1];stack,hints=stack_row(code)
        initial=bytes((x*73+39)&255 for x in range(256));expected=execute_native(code,initial)
        for limit in range(extent+1):
            off=next((x for x in sorted(hints,reverse=True) if x<limit),None)
            if off is None:actual=initial
            else:actual=execute_stack(stack,hints[off],off+1,initial)
            assert actual[:limit]==expected[:limit],(hex(ptr),limit)
            checked+=1
    result=dict(kernels=len(ptrs),rightByteBoundaries=checked,gameIntegrated=False)
    (BUILD/'stack_rows_verified.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
