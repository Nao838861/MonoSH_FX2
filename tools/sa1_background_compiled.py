"""現行の近景を4つのスクロール位相でコンパイルする。素材の色・輪郭は変えない。"""
import json,struct
import numpy as np
from sa1_compiled_rows import word_row

def build(source,dest):
    rom=bytearray(65536);cursor=0x100;pool={};height=9
    def alloc(data):
        nonlocal cursor
        data=bytes(data)
        if data in pool:return pool[data]
        a=cursor;rom[a:a+len(data)]=data;cursor+=len(data)
        if cursor>65536:raise ValueError('compiled near background exceeds bank FE')
        pool[data]=a;return a
    for phase in range(4):
        for y in range(height):
            row=np.frombuffer(source[0x8000+y*512:0x8000+(y+1)*512],dtype=np.uint8)
            row=np.roll(row,-phase)
            code,spans=word_row(row,0)
            table=bytearray();i=0;position=0
            for slot in range(129):
                while i<len(spans) and spans[i][0]<slot*2:
                    position+=spans[i][3];i+=1
                table+=struct.pack('<HH',position,spans[i][2] if i<len(spans) else 0)
            struct.pack_into('<HH',rom,(phase*height+y)*4,alloc(code),alloc(table))
    (dest/'compiled_background_packing.json').write_text(json.dumps({'nearHeight':height,'scrollPhases':4,'payloadBytes':cursor,'bank':'FE'},indent=2)+'\n')
    return rom
