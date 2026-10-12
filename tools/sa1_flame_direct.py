"""炎のnative左clip開始命令と必要なA初期値を直接保持する。"""
import struct


def encode(code,starts,extent):
    raw=bytearray()
    for limit in range(0,extent+1,2):
        pc=next((pc for off,pc in starts if off+1>=limit),len(code)-1)
        initial=0
        if code[pc]==0x9d:
            previous=pc-3
            while code[previous]!=0xa9:
                previous-=3
                assert previous>=0
            initial=struct.unpack_from('<H',code,previous+1)[0]
        assert pc<=255 and code[pc] in (0xa9,0xbd,0x9d,0x6b)
        raw+=bytes((pc,))+struct.pack('<H',initial)
    return raw
