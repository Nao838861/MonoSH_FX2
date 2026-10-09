"""既存のゲーム・画像を維持してSA-1実機コードへ接続する統合ビルド。"""
from pathlib import Path
import argparse
import hashlib,json,re,struct,subprocess
import numpy as np
from build_sa1_probe import assets,BUILD as ASSET_BUILD,ROOT,CC
from sa1_dma_rows import build as build_cache

GAME=ROOT/'game/v001'
SA1=ROOT/'game/sa1/v001'
BUILD=ROOT/'build/sa1_game'
BASE=ROOT/'build/game_v001'

def run(args):
    subprocess.run([str(a) for a in args],cwd=BUILD,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--renderer',choices=['dma','shared','compiled','macros'],default='macros');args=ap.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True)
    ASSET_BUILD.mkdir(parents=True,exist_ok=True)
    variants=assets()
    cfg=(GAME/'rom.cfg').read_text()
    cfg=re.sub(r'start=\$([45][0-9A-F])([0-9A-F]{4})',lambda m:'start=$'+f'{int(m[1],16)+0x80:02X}'+m[2],cfg)
    cfg=cfg.replace('  CPUCODE:', '  IRAM: start=$0200, size=$05C0, file="";\n  CPUCODE:')
    cfg=cfg.replace('  BOOT: load=BOOT, type=ro;', '  BOOT: load=BOOT, type=ro;\n  SA1: load=BOOT, run=IRAM, type=ro, define=yes;')
    (BUILD/'game.cfg').write_text(cfg)
    ppu=bytearray((BASE/'assets4/ppu.bin').read_bytes())
    for y in range(24):
        for x in range(32):struct.pack_into('<H',ppu,0xc000+2*(y*32+x),(y*32+x)|0x2400)
    (BUILD/'ppu_sa1.bin').write_bytes(ppu)
    definitions=['FX_4BPP','FX_FULL_TRANSFER','FX_SMOOTH_DEPTH','FX_GSU_UV','FX_GSU_CLIP','FX_FAST_OBJ','FX_DYNAMIC_DMA','FX_FINE_DMA','FX_DESCRIPTOR_DMA']
    defines=sum((['-D',s+'=1'] for s in definitions),[])+['-D','FX_DMA_ADMISSION_BYTES=9984']
    if args.renderer=='macros':defines+=['-D','SA1_PADDED=1']
    objs=[]
    renderer=SA1/('renderer_game_'+args.renderer+'.s' if args.renderer!='dma' else 'renderer_game.s')
    for name,src in [('cpu',SA1/'cpu_game.s'),('renderer',renderer),('dirty',SA1/'dirty_game.s'),('cover',SA1/'cover_game.s'),('fast',SA1/'fast_game.s'),('compact',SA1/'compact_game.s'),('objects',GAME/'objects4.s'),('ground',GAME/'ground.s')]:
        if name in ('objects','ground'):
            text=src.read_text(encoding='utf-8').replace('lda #$5f','lda #$df').replace('adc #$5a','adc #$da')
            if name=='objects':text=text.replace('  jsr fx4_wait_obj_blank','  nop\n  nop\n  nop')
            src=BUILD/(name+'.s');src.write_text(text,encoding='utf-8')
        obj=BUILD/(name+'_asm.o')
        run([CC/'ca65.exe',*defines,'-I',GAME,'-I',BASE,'-I',BUILD,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,src]);objs.append(obj)
    objs+=sorted(p for p in BASE.rglob('*.o') if p.name not in ('cpu_asm.o','ground_asm.o','objects_asm.o'))
    linked=BUILD/'linked.sfc'
    run([CC/'ld65.exe','-C',BUILD/'game.cfg','-m',BUILD/'game.map','-Ln',BUILD/'game.lbl','-o',linked,*objs,CC.parent/'lib/none.lib'])
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    legacy=linked.read_bytes();assert len(legacy)==0x200000
    if args.renderer=='shared':
        from sa1_shared_kernels import build as shared_cache
        rom=shared_cache(variants,BUILD,helper=labels['sa1_dma_span'],game=True)
    elif args.renderer in ('compiled','macros'):
        from sa1_game_compiled import build as compiled_cache
        rom=compiled_cache(variants,BUILD,macros=args.renderer=='macros')
    else:rom=build_cache(variants,BUILD,game=True)
    rom[:0x10000]=legacy[:0x10000]
    rom[0x400000:0x440000]=legacy[:0x40000]
    rom[0x591300:0x600000]=legacy[0x191300:0x200000]
    raw=(BASE/'assets4/background4.bin').read_bytes();bg=bytearray(65536)
    meta={k:int(v) for k,v in re.findall(r'(FX_BG_\w+) = (\d+)',(BASE/'assets4/background4.inc').read_text())}
    for parity in range(2):
        for y in range(meta['FX_BG_0_HEIGHT']):
            pixels=np.frombuffer(raw[y*512:(y+1)*512],dtype=np.uint8)
            pixels=np.roll(pixels,-parity)
            bg[parity*0x1000+y*256:parity*0x1000+(y+1)*256]=(pixels[::2]|pixels[1::2]<<4).tobytes()
    for phase in range(4):
        for y in range(meta['FX_BG_1_HEIGHT']):
            pixels=np.frombuffer(raw[0x8000+y*512:0x8000+(y+1)*512],dtype=np.uint8)
            pixels=np.roll(pixels,-phase)
            for x in range(0,512,4):
                val=sum(int(pixels[x+i])<<(i*4) for i in range(4))
                mask=sum((0 if pixels[x+i] else 15)<<(i*4) for i in range(4))
                struct.pack_into('<HH',bg,0x2000+phase*0x2000+y*512+x,mask,val)
    rom[0x5e0000:0x5f0000]=bg
    struct.pack_into('<H',rom,0x7ffc,labels['reset'])
    rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    path=BUILD/'MonoSHSA1_4bpp_game.sfc';path.write_bytes(rom)
    (BUILD/'manifest.json').write_text(json.dumps({'romSha256':hashlib.sha256(rom).hexdigest(),'sa1CodeBytes':labels['__SA1_SIZE__'],'renderer':args.renderer,'paddedFramebuffer':args.renderer=='macros','stage':'dirty-tiles-two-pages','goal60fpsAchieved':False},indent=2)+'\n')
    print(path)

if __name__=='__main__':main()
