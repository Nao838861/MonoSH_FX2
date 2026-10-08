"""独立した画素合成でGSUの4面、左右分割、VRAM世代を全画素照合する。"""
import json
import struct
import sys
import numpy as np
from PIL import Image
from build_game import GAME, BUILD
def prepare_draw(raw):
    center,bottom,w,h,asset,flags,_,_=raw
    if not w or not h:return None
    left=center-w//2;top=bottom-h-20
    width=min(256,left+w)-max(0,left);height=min(192,top+h)-max(0,top)
    if width<=0 or height<=0:return None
    color=json.loads((BUILD/'build_mode.json').read_text()).get('color',False)
    source=GAME/'assets'/('color4' if color else '')/f'{asset:02d}.png'
    aw,ah=Image.open(source).size
    du=aw*256//w;dv=ah*256//h
    u=max(0,-left)*du;v=max(0,-top)*dv
    if flags&16:u=aw*256-1-u;du=-du
    if flags&32:v=ah*256-1-v;dv=-dv
    v|=32768 if asset&1 else 0
    return max(0,left),max(0,top),du,dv,0,height,v,width,u,0x44+asset//2

def encode(pix):
    tiles=pix.reshape(24,8,32,8).transpose(2,0,1,3).reshape(768,8,8)
    out=np.zeros((768,32),dtype=np.uint8)
    for p in range(4):
        values=(((tiles>>p)&1)*np.array([128,64,32,16,8,4,2,1],dtype=np.uint8)).sum(axis=2)
        out[:,(p//2)*16+(p%2)+np.arange(8)*2]=values
    return out.tobytes()

def verify(directory):
    assets=BUILD/'assets4'
    banks={i:np.frombuffer((assets/f'bank{i:02x}.bin').read_bytes(),dtype=np.uint8) for i in range(0x44,0x5a)}
    backgrounds=np.frombuffer((assets/'background4.bin').read_bytes(),dtype=np.uint8)
    files=sorted(directory.glob('frame*_fb.bin'));assert files,'no captured 4bpp framebuffer'
    for path in files:
        prefix=path.name[:-7]
        packet=(directory/f'{prefix}_packet.bin').read_bytes()
        bg=(directory/f'{prefix}_background.bin').read_bytes()
        pix=np.zeros((192,256),dtype=np.uint8)
        for i in range(2):
            x,top,h,base=struct.unpack_from('<4H',bg,i*8)
            for dy in range(h):
                yy=top+dy
                if yy>=192:continue
                row=backgrounds[base+dy*512+(np.arange(256)+x)%512]
                pix[yy,row!=0]=row[row!=0]
        for i in range(struct.unpack_from('<H',packet)[0]):
            raw=struct.unpack_from('<hh6B',packet,32+i*10)
            command=prepare_draw(raw)
            if command is None:continue
            left,top,du,dv,_,h,v,w,u,bank=command
            xx=(((u+np.arange(w)*du)&65535)>>8)
            yy=((v+np.arange(h)*dv)&65535)&0xff00
            colors=banks[bank][yy[:,None]+xx[None,:]]
            target=pix[top:top+h,left:left+w]
            target[colors!=0]=colors[colors!=0]
        expected=encode(pix);actual=path.read_bytes()
        if expected!=actual:
            palette=struct.unpack('<16H',(assets/'palette4.bin').read_bytes())
            rgb=[tuple((v>>p&31)*255//31 for p in (0,5,10)) for v in palette]
            Image.fromarray(np.array(rgb,dtype=np.uint8)[pix]).save(directory/f'{prefix}_expected.png')
            raise AssertionError(f'{prefix}: {sum(x!=y for x,y in zip(actual,expected))} framebuffer bytes differ')
        meta=json.loads((directory/f'{prefix}_meta.json').read_text())
        vram=(directory/f'{prefix}_vram.bin').read_bytes();start=meta['page']*2
        assert vram[start:start+24576]==actual,f'{prefix}: visible VRAM has a mixed generation'
    print(f'{directory.name}: {len(files)} frames, all 49,152 indexed pixels and 24KiB visible VRAM match')

if __name__=='__main__':
    for name in sys.argv[1:] or ['play']:verify(BUILD/f'four_{name}')
