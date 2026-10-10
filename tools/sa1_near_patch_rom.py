"""48pxの近景補助だけをROMから直接実行する。素材・scroll全512通りを維持する。"""
import json,struct
import numpy as np


def build(source,dest,chunk_pixels=52):
    pixels=np.frombuffer(source[0x8000:0x8000+9*512],np.uint8).reshape(9,512)
    cache={};entries=[]
    for scroll in range(512):
        fine=scroll&7;left=(112-fine)&~3;right=(163-fine)&~3
        for y in range(9):
            row=pixels[y,(np.arange(left,right)+scroll)&511]
            # 48/52px窓は固定数の呼び出しに揃える。末尾の空kernelも測定する。
            for start in range(0,52,chunk_pixels):
                part=row[start:start+chunk_pixels]
                code=bytearray();acc=None
                for i in range(0,len(part),4):
                    word=part[i:i+4]
                    value=sum(int(c)<<(n*4) for n,c in enumerate(word))
                    if not value:continue
                    mask=sum((0 if c else 15)<<(n*4) for n,c in enumerate(word))
                    offset=struct.pack('<H',i//2)
                    if mask:
                        code+=b'\xbd'+offset+b'\x29'+struct.pack('<H',mask)+b'\x09'+struct.pack('<H',value)
                        acc=None
                    elif acc!=value:
                        code+=b'\xa9'+struct.pack('<H',value);acc=value
                    code+=b'\x9d'+offset
                code+=b'\x6b';key=bytes(code)
                cache.setdefault(key,len(cache));entries.append(key)
    table_bytes=len(entries)*2
    summary=dict(payloadBytes=table_bytes+sum(map(len,cache)),tableBytes=table_bytes,
                 kernelBytes=sum(map(len,cache)),uniqueKernels=len(cache),chunkPixels=chunk_pixels,
                 callsPerRow=(52+chunk_pixels-1)//chunk_pixels,
                 sourceScrolls=512,sourceRows=9,bank=0xfe,limitBytes=0xb000)
    summary['fits']=summary['payloadBytes']<=summary['limitBytes']
    if summary['fits']:
        payload=bytearray(table_bytes);offsets={}
        for key in cache:
            offsets[key]=len(payload);payload+=key
        for i,key in enumerate(entries):struct.pack_into('<H',payload,i*2,offsets[key])
        (dest/f'near_patch_rom_{chunk_pixels}.bin').write_bytes(payload)
    return summary


if __name__=='__main__':
    from build_sa1_game import BASE,BUILD
    source=(BASE/'assets4/background4.bin').read_bytes()
    measurements=[build(source,BUILD,n) for n in (52,28,20,16,12,8,4)]
    (BUILD/'near_patch_rom_packing.json').write_text(json.dumps(measurements,indent=2)+'\n')
    print(json.dumps(measurements))


def cyclic(source,dest):
    """全512開始位置の8px/4px断片を二つの空き領域へ置く。"""
    pixels=np.frombuffer(source[0x8000:0x8000+9*512],np.uint8).reshape(9,512)
    blocks=[];reports=[]
    for width,base,limit in ((8,0,0xb000),(4,0xc400,0x10000)):
        payload=bytearray(9*512*2);cache={}
        for y in range(9):
            for x in range(512):
                row=pixels[y,(np.arange(width)+x)&511];code=bytearray();acc=None
                for i in range(0,width,4):
                    word=row[i:i+4]
                    value=sum(int(c)<<(n*4) for n,c in enumerate(word))
                    if not value:continue
                    mask=sum((0 if c else 15)<<(n*4) for n,c in enumerate(word))
                    offset=struct.pack('<H',i//2)
                    if mask:
                        code+=b'\xbd'+offset+b'\x29'+struct.pack('<H',mask)+b'\x09'+struct.pack('<H',value)
                        acc=None
                    elif acc!=value:
                        code+=b'\xa9'+struct.pack('<H',value);acc=value
                    code+=b'\x9d'+offset
                code+=b'\x6b';key=bytes(code)
                if key not in cache:
                    cache[key]=base+len(payload);payload+=key
                struct.pack_into('<H',payload,(y*512+x)*2,cache[key])
        assert base+len(payload)<=limit,(width,base,len(payload),limit)
        blocks.append((base,payload));reports.append(dict(width=width,base=base,bytes=len(payload),uniqueKernels=len(cache)))
        (dest/f'near_cyclic_{width}.bin').write_bytes(payload)
    (dest/'near_cyclic_packing.json').write_text(json.dumps(reports,indent=2)+'\n')
    return blocks
