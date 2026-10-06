"""GSUの実出力を独立したPythonのUV/clip/flip/透明合成で照合する。"""
import json
from pathlib import Path
import struct
import sys
from PIL import Image
from build_game import BUILD, GAME

def is_obj(d):
    _,_,w,h,asset,_,_,priority=d
    return priority==2 and ((asset in [9,*range(15,31)] and (w,h)==(32,48)) or
                           (asset==10 and w==h and 1<=w<=16))

def packet_reference(draw, meta):
    objects=[struct.unpack_from('<hh6B',draw,i*10) for i in range(meta['count'])]
    objects.sort(key=lambda d:(d[7],-d[6]))
    output=[]
    for center,bottom,w,h,asset,flags,z,priority in objects:
        if is_obj((center,bottom,w,h,asset,flags,z,priority)): continue
        if flags&128 and meta['logic']&1: continue
        left=center-w//2;top=bottom-h-20
        sx=max(0,-left);sy=max(0,-top)
        width=min(256,left+w)-max(0,left);height=min(192,top+h)-max(0,top)
        if meta.get('gsuClip'):
            if meta.get('cpuClipCommands'):
                inside=w>0 and h>0 and left>=0 and top>=0 and left+w<=256 and top+h<=192
                output.append((center,bottom,w,h,asset,flags,0,128 if inside else 0))
            else:
                output.append((center,bottom,w,h,asset,flags,z,priority))
            continue
        if width<=0 or height<=0: continue
        aw,ah=Image.open(GAME/'assets'/f'{asset:02d}.png').size
        du=aw*256//w;dv=ah*256//h
        if meta.get('gsuUv'):
            attr=asset|((flags&48)<<2)
            output.append((max(0,left),max(0,top),w,h,max(0,left),height,
                           (32768 if asset&1 else 0)+sy,width,sx,(0x44+asset//2)|(attr<<8)))
            continue
        u=sx*du;v=sy*dv
        if flags&16: u=aw*256-1-u;du=-du
        if flags&32: v=ah*256-1-v;dv=-dv
        v+=32768 if asset&1 else 0
        output.append(tuple(x&65535 for x in (max(0,left),max(0,top),du,dv,max(0,left),height,v,width,u,0x44+asset//2)))
    return output

def prepare_uv(command,clip=False):
    left,top,w,h,x,height,base_skip,width,skip,packed_bank=command
    if clip:
        if left>=32768:left-=65536
        if top>=32768:top-=65536
        skip=max(0,-left);skip_y=max(0,-top)
        width=min(256,left+w)-max(0,left);height=min(192,top+h)-max(0,top)
        if width<=0 or height<=0:return None
        left=max(0,left);top=max(0,top);x=left
        base_skip|=skip_y
    attr=packed_bank>>8;asset=attr&63
    aw,ah=Image.open(GAME/'assets'/f'{asset:02d}.png').size
    du=aw*256//w;dv=ah*256//h
    u=skip*du;v=(base_skip&255)*dv
    if attr&64:u=aw*256-1-u;du=-du
    if attr&128:v=ah*256-1-v;dv=-dv
    v|=base_skip&32768
    return tuple(n&65535 for n in (left,top,du,dv,x,height,v,width,u,packed_bank&255))

def prepare_draw(draw):
    center,bottom,w,h,asset,flags,z,priority=draw
    attr=asset|((flags&48)<<2)
    wire=tuple(n&65535 for n in (center-w//2,bottom-h-20,w,h,0,h,
                               32768 if asset&1 else 0,w,0,(0x44+asset//2)|(attr<<8)))
    return prepare_uv(wire,True)

def verify(directory):
    banks={i:(GAME/'assets'/f'bank{i:02x}.bin').read_bytes() for i in range(0x44,0x5a)}
    samples=list(directory.glob('frame[0-9]*.bin'))
    assert samples, f'no samples: {directory}'
    for path in samples:
        number=path.stem[5:]
        raw=(directory/f'packet{number}.bin').read_bytes()
        draw=(directory/f'draw{number}.bin').read_bytes()
        meta=json.loads((directory/f'meta{number}.json').read_text())
        fmt='<hh6B' if meta.get('gsuClip') else '<10H'
        stride=struct.calcsize(fmt)
        commands=[struct.unpack_from(fmt,raw,32+i*stride) for i in range(struct.unpack_from('<H',raw)[0])]
        expected=packet_reference(draw,meta)
        assert commands==expected, f'UV/clip packet mismatch: {path}'
        if meta.get('gsuClip'):commands=[p for c in commands if (p:=prepare_draw(c))]
        elif meta.get('gsuUv'):commands=[prepare_uv(c) for c in commands]
        fb=bytearray(12288)
        for left,top,du,dv,x,height,v,width,u,bank in commands:
            for dy in range(height):
                vv=(v+dy*dv)&65535
                for dx in range(width):
                    uu=(u+dx*du)&65535
                    color=banks[bank][(vv&0xff00)+(uu>>8)]
                    if color==0: continue
                    px=left+dx;py=top+dy
                    addr=((px//8)*24+py//8)*16+(py&7)*2;bit=1<<(7-(px&7))
                    for plane in range(2):
                        fb[addr+plane]=(fb[addr+plane]&(~bit&255))|(bit if color&(1<<plane) else 0)
        actual=path.read_bytes()
        assert actual==fb, f'GSU pixels differ: {path}, {sum(a!=b for a,b in zip(actual,fb))} bytes'
    print(f'{directory.name}: {len(samples)} scenes, UV/clip packets and all 49,152 pixels match')

if __name__=='__main__':
    for name in (sys.argv[1:] or ['play']): verify(BUILD/name)
