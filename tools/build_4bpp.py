"""独立した4bpp/30fps実験。ゲームの60Hzロジックは共通ソースを利用する。"""
from pathlib import Path
import argparse
import json
import struct
import re
import sys
import numpy as np
from PIL import Image
import build_game as base
import build_objects

ASSETS=base.GAME/'assets'
PACK=base.BUILD/'assets4'

def augment_scale(scale):
    scale[0xb058:0xb084]=(PACK/'margin_slots.bin').read_bytes()
    raw=(PACK/'margin_tables.bin').read_bytes()
    scale[0xb100:0xb100+len(raw)]=raw

def ppu():
    old=(ASSETS/'ppu.bin').read_bytes()
    v=bytearray(65536)
    v[0xd000:0xf000]=old[0x4000:0x6000]
    for p in range(0,4096,2):
        word=struct.unpack_from('<H',old,0xa000+p)[0]
        struct.pack_into('<H',v,0xf000+p,word+256)
    for mapbase in (0xc000,0xc800):
        for y in range(32):
            for x in range(32):
                struct.pack_into('<H',v,mapbase+2*(32*y+x),(x*24+y if y<24 else 0)|0x2400)
    (PACK/'ppu.bin').write_bytes(v)
    # Mode1 BG3の2bppパレットはCGRAM 0..31。元のMode0 BG3は64..95。
    for bank in range(0x5a,0x5e):
        path=ASSETS/f'palette{bank:02x}.bin';raw=bytearray(path.read_bytes())
        for block in range(0,65536,128):
            p=block
            while raw[p]:
                raw[p+1]-=64;raw[p+2]-=64;p+=5
        (PACK/path.name).write_bytes(raw)

def assets(color):
    PACK.mkdir(parents=True,exist_ok=True)
    palette=[(0,0,0)]*16;palette[3]=(31,31,31)
    if color:
        palette=json.loads((ASSETS/'color4/palette.json').read_text())['rgb5']
    (PACK/'palette4.bin').write_bytes(struct.pack('<16H',*[r|(g<<5)|(b<<10) for r,g,b in palette]))
    (PACK/'source4.inc').write_text(f'FX4_COLOR = {int(color)}\n')
    images=[]
    for i in range(44):
        path=ASSETS/(f'color4/{i:02d}.png' if color else f'{i:02d}.png')
        image=Image.open(path).convert('RGBA');images.append(image)
    (PACK/'dimensions.bin').write_bytes(bytes(n for image in images for n in image.size))
    rgb=np.array(palette)*8+(np.array(palette)>>2)
    banks=[bytearray(65536) for _ in range(22)]
    pixels=[]
    for i,image in enumerate(images):
        a=np.array(image);opaque=a[:,:,3]>=128
        if color:
            pix=1+((a[:,:,:3,None].astype(np.int32)-rgb[1:].T[None,None,:,:])**2).sum(axis=2).argmin(axis=2)
        else:
            pix=np.where(a[:,:,:3].sum(axis=2)>=384,3,1)
        pix=np.where(opaque,pix,0).astype(np.uint8)
        pixels.append(pix)
        for y,row in enumerate(pix):
            offset=(i&1)*32768+y*256
            banks[i//2][offset:offset+image.width]=row.tobytes()
    holes=[]
    for i,image in enumerate(images):
        start=(i&1)*32768+image.height*256;end=(1+(i&1))*32768
        if start<end:holes.append([i//2,start,end])
    prescaled=bytearray(6144)
    geometry=(base.GAME/'upstream/monosh_boss_data.c').read_text()
    from smooth_depth import transform
    geometry=transform('monosh_boss_data',geometry)
    jobs=[]
    for slot,(i,kind) in enumerate(((13,'body'),(14,'face'),(5,'bom'),(39,'bom'),(40,'bom'),(41,'bom'))):
        vals=[int(x) for x in re.search('monosh_boss_'+kind+r'_geometry\[222\] = \{([^}]+)',geometry).group(1).replace('\n','').strip(',').split(',')]
        pix=pixels[i];h,w=pix.shape
        for width in sorted(set(vals[::2])):
            rowpix=pix[:,(np.arange(width)*(w*256//width))>>8]
            data=bytearray(h*2);offsets=[]
            for y,row in enumerate(rowpix):
                offsets.append(len(data));opaque_x=np.flatnonzero(row)
                if not len(opaque_x):data+=bytes((0,0));continue
                first=int(opaque_x[0]);last=int(opaque_x[-1])+1
                data+=bytes((first,last))
                packed=bytearray((last-(first&~1)+1)//2)
                for x in range(first&~1,last):packed[(x-(first&~1))//2]|=int(row[x])<<((x&1)*4)
                data+=packed
            jobs.append((slot,width,data,offsets))
    for slot,width,data,offsets in sorted(jobs,key=lambda job:-len(job[2])):
        hole=next(q for q in holes if q[2]-q[1]>=len(data))
        bank,offset,_=hole;hole[1]+=len(data)
        for y,relative in enumerate(offsets):struct.pack_into('<H',data,y*2,offset+relative)
        banks[bank][offset:offset+len(data)]=data
        struct.pack_into('<BBH',prescaled,slot*1024+width*4,0x44+bank,0,offset)
    # 原画の各行の未使用列も行境界表に使い、縮小原画用の大きな連続領域を残す。
    holes=[(i//2,(i&1)*32768+y*256+im.width,(i&1)*32768+(y+1)*256)
           for i,im in enumerate(images) for y in range(im.height)]+holes
    holes=[list(q) for q in holes]
    selected=[i for i in range(44) if i not in (5,9,10,13,14,38,39,40,41,42,43) and not 15<=i<=30]
    slots=bytearray([255]*44);tables=bytearray(len(selected)*768)
    for slot,i in enumerate(selected):
        slots[i]=slot;pix=pixels[i];h,w=pix.shape
        for width in range(1,256):
            du=w*256//width
            scaled=pix[:,(np.arange(width)*du)>>8]!=0
            first=scaled.argmax(axis=1);last=width-scaled[:,::-1].argmax(axis=1)
            padding=np.minimum(first,width-last).astype(np.uint8)
            padding[~scaled.any(axis=1)]=255
            hole=next(q for q in holes if q[2]-q[1]>=h)
            bank,offset,_=hole;hole[1]+=h
            banks[bank][offset:offset+h]=padding.tobytes()
            struct.pack_into('<BH',tables,slot*768+width*3,0x44+bank,offset)
    assert len(tables)<=0x4f00
    (PACK/'margin_slots.bin').write_bytes(slots);(PACK/'margin_tables.bin').write_bytes(tables)
    for i,raw in enumerate(banks):(PACK/f'bank{0x44+i:02x}.bin').write_bytes(raw)
    # 5Fは512px幅の遠景二層。画素参照はGSU、空のグラデーションは既存HDMA。
    far=bytearray(65536);meta=[]
    for i,name in enumerate(('far','near')):
        image=Image.open(ASSETS/f'recorded_effects/{name}_source.png').convert('RGBA')
        bbox=image.getbbox();image=image.crop((0,bbox[1],512,bbox[3]))
        a=np.array(image);mask=a[:,:,3]>=128
        if color:
            pix=1+((a[:,:,:3,None].astype(np.int32)-rgb[1:].T[None,None,:,:])**2).sum(axis=2).argmin(axis=2)
        else:pix=np.where(a[:,:,:3].sum(axis=2)>=384,3,1)
        pix=np.where(mask,pix,0).astype(np.uint8)
        assert pix.nbytes<=32768
        far[i*32768:i*32768+pix.nbytes]=pix.tobytes()
        meta.append({'top':bbox[1]-36,'height':image.height,'address':i*32768})
    assert meta[0]['height']*512<=0x2000
    far[0x2000:0x3800]=prescaled
    (PACK/'background4.bin').write_bytes(far)
    (PACK/'background4.inc').write_text('\n'.join(f'FX_BG_{i}_{k.upper()} = {v}' for i,m in enumerate(meta) for k,v in m.items())+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--color',action='store_true');args=parser.parse_args()
    config=json.loads((base.GAME/'config4.json' if (base.GAME/'config4.json').exists() else base.GAME/'config.json').read_text())
    config.update(bitsPerPixel=4,color=args.color,renderRateDivisor=2,fullFramebufferTransfer=True,stableGsuCache=False,
                  scaledRows=False,fastUv=False,rowMargins=False,genericPipeline=False,cpuClipCommands=False)
    (base.GAME/'config4.json').write_text(json.dumps(config,indent=2)+'\n')
    assets(args.color)
    base.pack_assets=lambda:None
    base.build_scaled=lambda *args:bytes(2048)
    build_objects.build=ppu
    sys.argv.append('--4bpp')
    base.main()
    mode=base.BUILD/'build_mode.json';m=json.loads(mode.read_text());m.update(bitsPerPixel=4,renderRateDivisor=2,color=args.color)
    mode.write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':main()
