"""途中命令からの実行結果を元の全行コード＋クリップと全位置で照合する。"""
import hashlib,json,re,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical


def execute(code,start,initial,buffer,origin):
    a=initial
    for i in range(start,len(code),3):
        op=code[i]
        if op==0x6b:return
        v=struct.unpack_from('<H',code,i+1)[0]
        if op==0xa9:a=v
        elif op==0xbd:a=struct.unpack_from('<H',buffer,origin+v)[0]
        elif op==0x29:a&=v
        elif op==0x09:a|=v
        elif op==0x9d:struct.pack_into('<H',buffer,origin+v,a)
        else:raise AssertionError(hex(op))
    raise AssertionError('missing RTL')


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    target=int(re.search(r'\$([0-9a-f]+)',(BUILD/'left_hints.inc').read_text())[1],16)
    table=rom[physical(target):physical(target)+2048*6]
    kernels=cases=0
    for slot in range(2048):
        ptr=int.from_bytes(table[slot*6:slot*6+3],'little')
        if not ptr:continue
        kernels+=1
        h=((ptr&65535)>>1 ^ ((ptr>>16)<<3))&2047
        for _ in range(2048):
            if int.from_bytes(table[h*6:h*6+3],'little')==ptr:break
            assert table[h*6:h*6+3]!=bytes(3),'hash stopped at empty slot'
            h=(h+1)&2047
        assert h==slot
        hint=int.from_bytes(table[slot*6+3:slot*6+6],'little')
        p=physical(ptr);code=rom[p:p+rom[p-2]];extent=rom[p-1]
        for cur in range(-extent+1,0):
            data=physical(hint)+(-cur//2)*3
            start=rom[data]*3;initial=struct.unpack_from('<H',rom,data+1)[0]
            background=bytearray((i*71+0xa5)&255 for i in range(512))
            full=background.copy();partial=background.copy()
            execute(code,0,0,full,128+cur)
            execute(code,start,initial,partial,128+cur)
            assert full[128:256]==partial[128:256],(hex(ptr),cur,start)
            cases+=1
    result={'kernels':kernels,'clippedRowsVerified':cases,'romSha256':hashlib.sha256(rom).hexdigest()}
    (BUILD/'left_hints_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
