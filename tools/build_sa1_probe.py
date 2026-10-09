"""現行の4bpp素材を変えず、実SA-1の描画を比較するROMを生成する。"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'game/sa1/v001'
BUILD=ROOT/'build/sa1_v001'
ART=ROOT/'game/v001/assets/color4'
CC=Path('D:/HomeBrew/CC65/bin')

def assets():
    palette=json.loads((ART/'palette.json').read_text())['rgb5']
    rgb=np.array(palette,dtype=np.int32)*8+(np.array(palette,dtype=np.int32)>>2)
    banks=[bytearray(65536) for _ in range(32)]
    dims=[]; manifest={}; variants={}; extra=44
    for asset in range(44):
        for phase in range(3 if asset in (6,7,8,31,37) else 1):
            name=f'{asset:02d}'+(f'_hue{phase}' if phase else '')+'.png'
            path=ART/name
            manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            a=np.array(Image.open(path).convert('RGBA')); h,w=a.shape[:2]
            pix=np.where(a[:,:,3]>=128,1+((a[:,:,:3,None].astype(np.int32)-rgb[1:].T[None,None,:,:])**2).sum(axis=2).argmin(axis=2),0).astype(np.uint8)
            if phase==0:
                slot=asset; dims.extend((w,h))
            else:slot=extra;extra+=1
            variants[(asset,phase)]=(slot,pix)
            bank=slot//2; offset=(slot%2)*32768
            while bank>=len(banks): banks.append(bytearray(65536))
            for y,row in enumerate(pix):banks[bank][offset+y*256:offset+y*256+w]=row.tobytes()
    # 全assetのsourceとQ8.8ステップ。基準段階では画素ごとに加算する。
    lookup=bytearray(44*3*4)
    for asset in range(44):
        for phase in range(3):
            slot,_=variants.get((asset,phase),variants[(asset,0)])
            struct.pack_into('<HBB',lookup,(asset*3+phase)*4,(slot%2)*32768,0xc4+slot//2,0)
    (BUILD/'lookup.bin').write_bytes(lookup)
    (BUILD/'dimensions.bin').write_bytes(bytes(dims))
    scale=bytearray(65536)
    for axis in (0,1):
        for i in range(44):
            struct.pack_into('<256H',scale,axis*0x5800+i*512,*[dims[i*2+axis]*256//n if n else 0 for n in range(256)])
    (BUILD/'scale.bin').write_bytes(scale)
    for i,bank in enumerate(banks[:27]):(BUILD/f'raw{i:02d}.bin').write_bytes(bank)
    (BUILD/'palette.bin').write_bytes(struct.pack('<16H',*[r|(g<<5)|(b<<10) for r,g,b in palette]))
    (BUILD/'asset_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return variants

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['baseline','prescaled','compiled','dma_rows','shared'],default='baseline');ap.add_argument('--dma-clear',action='store_true');args=ap.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True);variants=assets()
    cfg='MEMORY {\n BOOT: start=$008000, size=$7fb0, file=%O, fill=yes, fillval=$ea;\n HEADER: start=$00ffb0, size=$50, file=%O, fill=yes;\n PAD0: start=$018000, size=$8000, file=%O, fill=yes;\n IRAM: start=$0200, size=$0600, file="";\n'
    bank_count=128 if args.mode!='baseline' else 32
    for b in range(1,bank_count):cfg+=f' B{b:02X}: start=${b:02x}0000, size=$10000, file=%O, fill=yes;\n'
    cfg+='}\nSEGMENTS {\n BOOT: load=BOOT, type=ro;\n HEADER: load=HEADER, type=ro;\n SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n'
    if args.mode=='baseline':
        for b in range(4,31):cfg+=f' RAW{b:02X}: load=B{b:02X}, type=ro;\n'
        cfg+=' SCALE: load=B1F, type=ro;\n'
    cfg+='}\n'
    (BUILD/'probe.cfg').write_text(cfg)
    generated=''
    if args.mode=='baseline':
        for b in range(4,31):generated+=f'.segment "RAW{b:02X}"\n.incbin "raw{b-4:02d}.bin"\n'
        generated+='.segment "SCALE"\n.incbin "scale.bin"\n'
    (BUILD/'data.s').write_text(generated)
    objs=[]
    for name,source in [('probe',GAME/'probe.s'),('renderer',GAME/'renderer.s'),('data',BUILD/'data.s')]:
        if name=='renderer' and args.mode=='compiled':source=GAME/'renderer_compiled.s'
        if name=='renderer' and args.mode=='dma_rows':source=GAME/'renderer_dma.s'
        if name=='renderer' and args.mode=='shared':source=GAME/'renderer_shared.s'
        obj=BUILD/f'{name}.o'
        subprocess.run([str(CC/'ca65.exe'),*(['-D','SA1_DMA_CLEAR=1'] if args.dma_clear else []),*(['-D','SA1_PRESCALED=1'] if args.mode!='baseline' else []),'-I',str(BUILD),'-o',str(obj),str(source)],cwd=BUILD,check=True);objs.append(str(obj))
    rom=BUILD/f'MonoSHSA1_{args.mode}_probe.sfc'
    subprocess.run([str(CC/'ld65.exe'),'-C',str(BUILD/'probe.cfg'),'-m',str(BUILD/'probe.map'),'-Ln',str(BUILD/'probe.lbl'),'-o',str(rom),*objs],check=True)
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'probe.lbl').read_text())}
    raw=bytearray(rom.read_bytes());assert len(raw)==bank_count*65536
    if args.mode!='baseline':
        if args.mode=='prescaled':from sa1_prescaled import build
        elif args.mode=='compiled':from sa1_compiled_rows import build
        elif args.mode=='dma_rows':from sa1_dma_rows import build
        else:from sa1_shared_kernels import build
        cache=build(variants,BUILD,helper=labels['sa1_dma_span']) if args.mode=='shared' else build(variants,BUILD)
        raw[0x10000:]=cache[0x10000:]
    struct.pack_into('<H',raw,0x7ffc,labels['reset']);raw[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(raw)&65535;struct.pack_into('<HH',raw,0x7fdc,checksum^65535,checksum);rom.write_bytes(raw)
    mode=vars(args)|{'romSha256':hashlib.sha256(raw).hexdigest(),'labelsSha256':hashlib.sha256((BUILD/'probe.lbl').read_bytes()).hexdigest()}
    (BUILD/'mode.json').write_text(json.dumps(mode,indent=2)+'\n')
    print(f'Built {rom} / SA-1 kernel {labels["__SA1_SIZE__"]} bytes')

if __name__=='__main__':main()
