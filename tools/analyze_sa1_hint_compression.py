"""左端hintを8個ごとのcheckpointと2bit差分で保持する容量を測る。"""
import json,re,struct
from build_sa1_game import BUILD
from sa1_left_hints import physical


DELTAS=(0,1,2,4)


def compress(raw):
    out=bytearray((128,))
    for start in range(0,len(raw),8):
        block=raw[start:start+8];bits=0
        for i in range(1,len(block)):
            bits|=DELTAS.index(block[i]-block[i-1])<<((i-1)*2)
        out+=bytes((block[0],bits&255,bits>>8))
    return bytes(out) if len(out)<len(raw) else raw


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    info=json.loads((BUILD/'left_hints_packing.json').read_text())
    target=int(re.search(r'\$([0-9a-f]+)',(BUILD/'left_hints.inc').read_text())[1],16)
    table=rom[physical(target):physical(target)+info['hashBytes']]
    raw_pool=set();compressed_pool=set();boundaries=0
    for i in range(0,len(table),6):
        ptr=int.from_bytes(table[i:i+3],'little')
        if not ptr:continue
        p=physical(ptr);extent=rom[p-1];n=(extent+1)//2+1
        hint=physical(int.from_bytes(table[i+3:i+6],'little'))
        if info.get('compressed') and rom[hint]==128:
            raw=bytearray()
            for index in range(n):
                pos=hint+1+(index//8)*3
                bits=rom[pos+1]|rom[pos+2]<<8
                raw.append(rom[pos]+sum(DELTAS[bits>>(j*2)&3] for j in range(index%8)))
            raw=bytes(raw)
        else:raw=rom[hint:hint+n]
        # ROM内のnative命令から、各clip境界の実際の開始命令を求める。
        code=rom[p:p+rom[p-2]];stores=[];begin=0
        for pc in range(0,len(code)-1,3):
            if code[pc]==0x9d:
                stores.append((struct.unpack_from('<H',code,pc+1)[0],begin));begin=pc+3
        expected=bytes(next((pc//3 for off,pc in stores if off+1>=index*2),(len(code)-1)//3) for index in range(n))
        assert raw==expected, f'clip hints disagree with native code {ptr:06x}'
        packed=compress(raw);raw_pool.add(raw);compressed_pool.add(packed)
        for index,expected in enumerate(raw):
            if packed[0]&128:
                group=index//8;within=index%8;pos=1+group*3
                bits=packed[pos+1]|packed[pos+2]<<8
                actual=packed[pos]+sum(DELTAS[bits>>(j*2)&3] for j in range(within))
            else:actual=packed[index]
            assert actual==expected
            boundaries+=1
    result=dict(kernels=info['kernels'],boundaries=boundaries,originalBytes=sum(map(len,raw_pool)),
        compressedBytes=sum(map(len,compressed_pool)),allOriginalHintsRetained=True,gameIntegrated=info.get('compressed',False))
    result['savedBytes']=result['originalBytes']-result['compressedBytes']
    (BUILD/'hint_compression_capacity.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
