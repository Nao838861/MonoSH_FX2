"""既存の全寸法を残し、爆発のstack描画コードを追加する容量を測る。"""
import json,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical


def stack_row(code):
    words=[];value=None;mask=0
    for i in range(0,len(code)-1,3):
        op=code[i];operand=struct.unpack_from('<H',code,i+1)[0]
        if op==0xa9:value=operand;mask=0
        elif op==0xbd:mask=None
        elif op==0x29:mask=operand
        elif op==0x09:value=operand
        elif op==0x9d:
            assert value is not None and mask is not None
            words.append((operand,mask,value));mask=0
        else:raise ValueError(hex(op))
    out=bytearray();hints={};previous=words[-1][0]+2 if words else 0
    for off,mask,value in reversed(words):
        gap=previous-(off+2)
        if gap:out+=b'\x3b\x38\xe9'+struct.pack('<H',gap)+b'\x1b'
        # 右端を落とす場合は、この位置から実行してSを当該word末尾に置く。
        hints[off]=len(out)
        if mask:out+=b'\xbd'+struct.pack('<H',off)+b'\x29'+struct.pack('<H',mask)+b'\x09'+struct.pack('<H',value)+b'\x48'
        else:out+=b'\xf4'+struct.pack('<H',value)
        previous=off
    out+=b'\x5c\x00\x07\x00'
    return bytes(out),hints


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes();cases=[]
    for targets,widths in (((39,40,41),(94,)),((40,41),(94,)),((40,),(94,)),((39,40,41),tuple(range(90,256))),((39,40,41),tuple(range(80,256)))):
        codes=set();hint_tables=set();entries=0;rows=0;per_asset=[]
        for asset in targets:
            found=set()
            for w in widths:
                block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
                if not block:continue
                for i in range(rom[0x7f0000+block]):
                    entry=0x7f0000+block+1+i*10;h=rom[entry]
                    desc=struct.unpack_from('<H',rom,entry+1)[0]
                    entries+=2;rows+=h*2
                    for parity in range(2):
                        p=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                        for y in range(h):
                            q=p+y*11;assert rom[q]==0xa9 and rom[q+7]==0x22
                            found.add(int.from_bytes(rom[q+8:q+11],'little'))
            for ptr in found:
                p=physical(ptr);code=rom[p:p+rom[p-2]]
                stack,hints=stack_row(code);codes.add(stack)
                extent=rom[p-1]
                assert len(stack)<=255
                raw=bytearray()
                for end in range(0,extent+1,2):
                    off=next((x for x in sorted(hints,reverse=True) if x<end),None)
                    raw+=bytes((hints[off],off+2)) if off is not None else bytes((len(stack)-4,0))
                hint_tables.add(bytes(raw))
            per_asset.append(dict(asset=asset,kernels=len(found)))
        cases.append(dict(minWidth=min(widths),maxWidth=max(widths),perAsset=per_asset,
            uniqueStackKernels=len(codes),stackCodeBytes=sum(map(len,codes)),
            rightHintBytes=sum(map(len,hint_tables)),geometryEntries=entries,rowUses=rows,
            rowDescriptorBytes=rows*8,gameIntegrated=False))
    (BUILD/'stack_capacity.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(cases))


if __name__=='__main__':main()
