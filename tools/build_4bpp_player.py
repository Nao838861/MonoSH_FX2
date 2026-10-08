"""自機17姿勢を専用OBJ色のまま保存し、表示姿勢だけ896bytes転送する。"""
import struct
from pathlib import Path
from PIL import Image

PLAYERS=[9,*range(15,31)]
FRAME_BYTES=896
ROM_BASE=0xc000

def build(assets,pack,bank):
    offsets=[0]*44
    for pose,asset in enumerate(PLAYERS):
        image=Image.open(assets/'obj_color'/f'{asset:02d}.png')
        assert image.mode=='P' and image.size==(32,48)
        raw=bytearray(FRAME_BYTES)
        for part in range(6):
            ox=(part%2)*16;oy=(part//2)*16
            for ty in range(2):
                for tx in range(2):
                    tile=part*2+ty*16+tx
                    for y in range(8):
                        for plane in range(4):
                            raw[tile*32+(plane//2)*16+y*2+(plane&1)]=sum(
                                ((image.getpixel((ox+tx*8+x,oy+ty*8+y))>>plane)&1)<<(7-x)
                                for x in range(8))
        start=ROM_BASE+pose*FRAME_BYTES
        assert start+FRAME_BYTES<=65536
        bank[start:start+FRAME_BYTES]=raw;offsets[asset]=start
    (pack/'player_obj.inc').write_text('player4_offsets:\n.word '+','.join(map(str,offsets))+'\n')
    (pack/'player_obj.json').write_text(__import__('json').dumps({'assets':PLAYERS,'frameBytes':FRAME_BYTES,'romBank':0x5f,'romBase':ROM_BASE,'vramBase':0xc800,'tileBase':64},indent=2)+'\n')
