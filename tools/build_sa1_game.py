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
    ap=argparse.ArgumentParser();ap.add_argument('--renderer',choices=['dma','shared','compiled','macros'],default='macros');ap.add_argument('--bucket-sort',action='store_true');ap.add_argument('--tile-dma',action='store_true');ap.add_argument('--pipeline',action='store_true');ap.add_argument('--pipeline-direct',action='store_true');ap.add_argument('--pipeline-irq',action='store_true');ap.add_argument('--temporal-sort',action='store_true');ap.add_argument('--shape-cache',action='store_true');ap.add_argument('--cpu-far',action='store_true');ap.add_argument('--cpu-fill',action='store_true');ap.add_argument('--cpu-code-copy',action='store_true');ap.add_argument('--fast-dma',action='store_true');ap.add_argument('--triple-bw',action='store_true');ap.add_argument('--large-edge-cache',action='store_true');ap.add_argument('--padded-pipeline',action='store_true');ap.add_argument('--clip-edges',action='store_true');ap.add_argument('--merge-dma',action='store_true');ap.add_argument('--redraw-all',action='store_true');ap.add_argument('--transfer-tiles',action='store_true');ap.add_argument('--pipeline-depth',type=int,choices=[3,4,5],default=3);args=ap.parse_args()
    assert not args.temporal_sort or args.pipeline
    assert not args.cpu_far or (args.pipeline_direct and args.pipeline_irq)
    assert not args.cpu_fill or (args.pipeline_direct and args.pipeline_irq)
    assert not args.cpu_code_copy or (args.pipeline and args.pipeline_irq)
    assert not args.fast_dma or args.pipeline
    assert not args.triple_bw or (args.pipeline_direct and args.redraw_all)
    assert not args.large_edge_cache or (args.pipeline and args.pipeline_direct and not args.clip_edges)
    assert not args.padded_pipeline or (args.pipeline and args.redraw_all and not args.pipeline_direct and not args.merge_dma and not args.transfer_tiles and not args.clip_edges)
    assert not args.clip_edges or (args.pipeline and args.redraw_all)
    assert not args.merge_dma or (args.pipeline and args.pipeline_direct and not args.transfer_tiles)
    assert not args.redraw_all or args.renderer=='macros'
    assert not (args.tile_dma and args.bucket_sort),'experimental bucket storage overlaps large tile descriptor lists'
    assert not args.pipeline_direct or args.pipeline
    assert not args.pipeline_irq or args.pipeline
    assert not args.transfer_tiles or (args.pipeline and args.pipeline_direct)
    assert not args.pipeline or (args.renderer=='macros' and not args.tile_dma and not args.bucket_sort)
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
    definitions=['FX_4BPP','FX_FULL_TRANSFER','FX_SMOOTH_DEPTH','FX_GSU_UV','FX_GSU_CLIP','FX_FAST_OBJ','FX_DYNAMIC_DMA','FX_FINE_DMA','FX_DESCRIPTOR_DMA','FX_GROUND_CACHE']
    defines=sum((['-D',s+'=1'] for s in definitions),[])+['-D','FX_DMA_ADMISSION_BYTES=9984']
    if args.shape_cache:defines+=['-D','SA1_SHAPE_CACHE=1']
    if args.bucket_sort:defines+=['-D','SA1_SORT=1']
    if args.tile_dma:defines+=['-D','SA1_TILE_DMA=1']
    if args.transfer_tiles:defines+=['-D','SA1_TRANSFER_TILES=1']
    if args.pipeline:defines+=['-D','SA1_PIPELINE=1','-D',f'SA1_PIPELINE_DEPTH={args.pipeline_depth}']
    if args.fast_dma:defines+=['-D','SA1_FAST_DMA=1']
    if args.triple_bw:defines+=['-D','SA1_TRIPLE_BW=1']
    if args.pipeline_direct:defines+=['-D','SA1_PIPELINE_DIRECT=1']
    if args.pipeline_irq:defines+=['-D','SA1_PIPELINE_IRQ=1']
    if args.renderer=='macros':
        defines+=['-D','SA1_PADDED=1']
        if not args.padded_pipeline:defines+=['-D','SA1_DIRECT=1']
    if args.padded_pipeline:defines+=['-D','SA1_PIPELINE_PADDED=1']
    objs=[]
    renderer=SA1/('renderer_game_'+args.renderer+'.s' if args.renderer!='dma' else 'renderer_game.s')
    for name,src in [('cpu',SA1/'cpu_game.s'),('renderer',renderer),('dirty',SA1/'dirty_game.s'),('tiles',SA1/'tiles_game.s'),('shape',SA1/'shape_game.s'),('cover',SA1/'cover_game.s'),('fast',SA1/'fast_game.s'),('edge',SA1/'edge_cached_game.s'),('compact',SA1/'compact_game.s'),('near',SA1/'near_game.s'),('sort',SA1/'sort_game.s'),('packet',GAME/'packet.s'),('objects',GAME/'objects4.s'),('ground',GAME/'ground.s')]:
        if args.pipeline and name=='sort':continue
        if name in ('objects','ground'):
            text=src.read_text(encoding='utf-8').replace('lda #$5f','lda #$df').replace('adc #$5a','adc #$da')
            if name=='objects':text=text.replace('  jsr fx4_wait_obj_blank','  nop\n  nop\n  nop')
            if name=='objects' and args.pipeline:
                text+='\n.export player4_next\n.import pipe_obj_pointer\n'
                text=text.replace('lda #fx_obj_present+128','lda pipe_obj_pointer\n  clc\n  adc #128').replace('lda #fx_obj_present','lda pipe_obj_pointer')
            if name=='ground' and args.pipeline:text='.import pipe_ground_wait\n'+text.replace('_fx_build_ground:\n','_fx_build_ground:\n  jsr pipe_ground_wait\n')
            if name=='ground' and args.pipeline:
                from sa1_pipeline_sources import ground_buffers
                text=ground_buffers(text,args.pipeline_depth)
            src=BUILD/(name+'.s');src.write_text(text,encoding='utf-8')
        elif args.pipeline:
            from sa1_pipeline_sources import prepare
            generated=prepare(name,src.read_text(encoding='utf-8'),direct=args.pipeline_direct,irq=args.pipeline_irq,transfer_tiles=args.transfer_tiles,merge_dma=args.merge_dma,padded=args.padded_pipeline,large_edge=args.large_edge_cache,triple_bw=args.triple_bw,cpu_copy=args.cpu_code_copy,cpu_fill=args.cpu_fill,cpu_far=args.cpu_far)
            src=BUILD/(name+'_pipeline.s');src.write_text(generated,encoding='utf-8')
        if name=='packet' and args.temporal_sort:
            text=src.read_text(encoding='utf-8')
            text='.import sa1_temporal_prepare, sa1_temporal_save\n'+text
            text=text.replace('  sty packet_work+8', '  sty packet_work+8\n  jsr sa1_temporal_prepare\n  ;')
            text=text.replace('  beq insert\n  sta keys+2,y', '  bne temporal_move\n  lda order,y\n  cmp packet_work+26\n  bcc insert\n  beq insert\n  lda keys,y\ntemporal_move:\n  sta keys+2,y')
            text=text.replace('sorted:\n', 'sorted:\n  jsr sa1_temporal_save\n')
            src=BUILD/'packet_temporal.s';src.write_text(text,encoding='utf-8')
        if name=='renderer' and args.clip_edges:
            text=src.read_text(encoding='utf-8').replace('  lda $0120,x\n  sta dirtyL\n  lda $0122,x\n  sta dirtyR', '  lda #0\n  sta dirtyL\n  lda #128\n  sta dirtyR')
            text=text.replace('  lda dirtyL\n  cmp $b4', '  lda edge\n  jne row_partial\n  lda dirtyL\n  cmp $b4')
            src=BUILD/'renderer_clip_edges.s';src.write_text(text,encoding='utf-8')
        if name=='fast' and args.redraw_all:
            text=src.read_text(encoding='utf-8').replace('fast_tiles:\n','fast_tiles:\n  jmp fast_base_ready\n')
            if args.clip_edges:text=text.replace('  jsl sa1_edge_prepare\n','  jsl sa1_edge_prepare\n  lda $c4\n  jne fast_fail\n')
            src=BUILD/'fast_redraw_all.s';src.write_text(text,encoding='utf-8')
        obj=BUILD/(name+'_asm.o')
        run([CC/'ca65.exe',*defines,*(['-D','SA1_TILE_DMA=1'] if args.transfer_tiles and name=='dirty' else []),'-I',GAME,'-I',SA1,'-I',BASE,'-I',BUILD,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,src]);objs.append(obj)
    if args.pipeline:
        obj=BUILD/'pipeline_asm.o'
        run([CC/'ca65.exe',*defines,'-I',SA1,'-o',obj,SA1/'pipeline_sa1.s']);objs.append(obj)
    if args.temporal_sort:
        obj=BUILD/'temporal_sort.o';run([CC/'ca65.exe','-o',obj,SA1/'temporal_sort_game.s']);objs.append(obj)
    if args.cpu_fill or args.cpu_far:
        obj=BUILD/'cpu_fill.o';run([CC/'ca65.exe','-o',obj,SA1/'cpu_fill_game.s']);objs.append(obj)
    if args.merge_dma:
        obj=BUILD/'merge_dma.o';run([CC/'ca65.exe','-o',obj,SA1/'merge_dma.s']);objs.append(obj)
    objs+=sorted(p for p in BASE.rglob('*.o') if p.name not in ('cpu_asm.o','ground_asm.o','objects_asm.o','packet_asm.o'))
    linked=BUILD/'linked.sfc'
    run([CC/'ld65.exe','-C',BUILD/'game.cfg','-m',BUILD/'game.map','-Ln',BUILD/'game.lbl','-o',linked,*objs,CC.parent/'lib/none.lib'])
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    legacy=linked.read_bytes();assert len(legacy)==0x200000
    if args.renderer=='shared':
        from sa1_shared_kernels import build as shared_cache
        rom=shared_cache(variants,BUILD,helper=labels['sa1_dma_span'],game=True)
    elif args.renderer in ('compiled','macros'):
        from sa1_game_compiled import build as compiled_cache
        fingerprint=hashlib.sha256()
        for path in [ROOT/'tools'/name for name in ('sa1_game_compiled.py','sa1_patterns.py','smooth_depth.py','test_sa1_probe.py','sa1_prescaled.py')]+[GAME/'packet.s']+sorted((GAME/'upstream').glob('*.c')):
            fingerprint.update(path.read_bytes())
        for key,value in sorted(variants.items()):
            fingerprint.update(str(key).encode());fingerprint.update(value[1].tobytes());fingerprint.update(str(value[1].shape).encode())
        stride=256 if args.padded_pipeline else 128
        key=fingerprint.hexdigest()+args.renderer+str(stride)
        suffix='_256' if args.padded_pipeline else ''
        cache=BUILD/('compiled_cache'+suffix+'.bin');metadata=BUILD/('compiled_cache'+suffix+'.json')
        if cache.exists() and metadata.exists() and json.loads(metadata.read_text()).get('key')==key:
            rom=bytearray(cache.read_bytes())
            (BUILD/'compiled_game_packing.json').write_text(json.dumps(json.loads(metadata.read_text())['packing'],indent=2)+'\n')
        else:
            rom=compiled_cache(variants,BUILD,macros=args.renderer=='macros',stride=stride)
            cache.write_bytes(rom)
            metadata.write_text(json.dumps({'key':key,'packing':json.loads((BUILD/'compiled_game_packing.json').read_text())}))
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
    if args.renderer=='macros':
        from sa1_background_compiled import build as compiled_background
        assert json.loads((BUILD/'compiled_game_packing.json').read_text())['payloadEnd']<=0x7e0000
        rom[0x7e0000:0x7f0000]=compiled_background(raw,BUILD)
    struct.pack_into('<H',rom,0x7ffc,labels['reset'])
    struct.pack_into('<H',rom,0x7fea,labels['nmi_game'])
    struct.pack_into('<H',rom,0x7ffa,labels['nmi_game'])
    if args.pipeline:
        struct.pack_into('<H',rom,0x7fee,labels['irq_game'])
        struct.pack_into('<H',rom,0x7ffe,labels['irq_game'])
    rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    path=BUILD/'MonoSHSA1_4bpp_game.sfc';path.write_bytes(rom)
    (BUILD/'manifest.json').write_text(json.dumps({'romSha256':hashlib.sha256(rom).hexdigest(),'sa1CodeBytes':labels['__SA1_SIZE__'],'renderer':args.renderer,'paddedFramebuffer':False,'directFramebuffer':args.renderer=='macros','tileDma':args.tile_dma,'bucketSort':args.bucket_sort,'pipeline':args.pipeline,'pipelineDirect':args.pipeline_direct,'pipelineIrq':args.pipeline_irq,'pipelineDepth':args.pipeline_depth,'transferTiles':args.transfer_tiles,'redrawAll':args.redraw_all,'mergeDma':args.merge_dma,'clipEdges':args.clip_edges,'paddedPipeline':args.padded_pipeline,'workingFramebufferStride':256 if args.padded_pipeline else 128,'largeEdgeCache':args.large_edge_cache,'tripleBw':args.triple_bw,'fastDma':args.fast_dma,'cpuCodeCopy':args.cpu_code_copy,'cpuFill':args.cpu_fill,'cpuFar':args.cpu_far,'shapeCache':args.shape_cache,'temporalSort':args.temporal_sort,'stage':'dirty-tiles-two-pages','goal60fpsAchieved':False},indent=2)+'\n')
    print(path)

if __name__=='__main__':main()
