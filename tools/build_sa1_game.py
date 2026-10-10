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
    ap=argparse.ArgumentParser();ap.add_argument('--renderer',choices=['dma','shared','compiled','macros'],default='macros');ap.add_argument('--bucket-sort',action='store_true');ap.add_argument('--tile-dma',action='store_true');ap.add_argument('--pipeline',action='store_true');ap.add_argument('--pipeline-direct',action='store_true');ap.add_argument('--pipeline-irq',action='store_true');ap.add_argument('--wait-slots',action='store_true');ap.add_argument('--row-dirty-bands',action='store_true');ap.add_argument('--row-dirty',action='store_true');ap.add_argument('--front-delta',action='store_true');ap.add_argument('--native-background',action='store_true');ap.add_argument('--native-far',action='store_true');ap.add_argument('--key-buckets',action='store_true');ap.add_argument('--radix-sort',action='store_true');ap.add_argument('--adaptive-vram',action='store_true');ap.add_argument('--offload-sort',action='store_true');ap.add_argument('--fastrom-cpu',action='store_true');ap.add_argument('--packet-shapes',action='store_true');ap.add_argument('--prefill-pipeline',action='store_true');ap.add_argument('--cpu-edge-copy',action='store_true');ap.add_argument('--skip-far-clear',action='store_true');ap.add_argument('--linear-shape',action='store_true');ap.add_argument('--fast-left-clip',action='store_true');ap.add_argument('--staged-conversion',action='store_true');ap.add_argument('--temporal-sort',action='store_true');ap.add_argument('--shape-cache',action='store_true');ap.add_argument('--cpu-far',action='store_true');ap.add_argument('--cpu-fill',action='store_true');ap.add_argument('--cpu-code-copy',action='store_true');ap.add_argument('--fast-dma',action='store_true');ap.add_argument('--triple-bw',action='store_true');ap.add_argument('--large-edge-cache',action='store_true');ap.add_argument('--padded-pipeline',action='store_true');ap.add_argument('--clip-edges',action='store_true');ap.add_argument('--merge-dma',action='store_true');ap.add_argument('--redraw-all',action='store_true');ap.add_argument('--transfer-tiles',action='store_true');ap.add_argument('--pipeline-depth',type=int,choices=[3,4,5],default=3);args=ap.parse_args()
    assert not args.wait_slots or args.pipeline_irq
    assert not args.row_dirty_bands or args.row_dirty
    assert not args.row_dirty or (args.pipeline_direct and args.renderer=='macros' and not args.transfer_tiles)
    if args.front_delta:
        assert args.native_background
        args.adaptive_vram=True
    if args.native_background:args.native_far=True
    assert not args.native_far or (args.pipeline_direct and not args.skip_far_clear and not args.fastrom_cpu)
    assert not args.key_buckets or (args.pipeline and not args.radix_sort and not args.temporal_sort and not args.offload_sort)
    assert not args.radix_sort or (args.pipeline and not args.temporal_sort and not args.offload_sort)
    assert not args.adaptive_vram or (args.pipeline_direct and args.triple_bw and args.fast_dma and args.merge_dma and not args.staged_conversion and not args.transfer_tiles)
    assert not args.offload_sort or (args.pipeline_irq and args.large_edge_cache and not args.staged_conversion and not args.fastrom_cpu and not args.temporal_sort)
    assert not args.packet_shapes or (args.pipeline and args.renderer=='macros')
    assert not args.prefill_pipeline or (args.triple_bw and args.pipeline_depth==5)
    assert not args.cpu_edge_copy or (args.large_edge_cache and args.cpu_code_copy)
    assert not args.fast_left_clip or args.clip_edges
    assert not args.staged_conversion or (args.pipeline_direct and args.pipeline_irq and args.large_edge_cache)
    assert not args.temporal_sort or args.pipeline
    assert not args.cpu_far or (args.pipeline_direct and args.pipeline_irq)
    assert not args.cpu_fill or (args.pipeline_direct and args.pipeline_irq)
    assert not args.cpu_code_copy or (args.pipeline and args.pipeline_irq)
    assert not args.fast_dma or args.pipeline
    assert not args.triple_bw or (args.pipeline_direct and args.redraw_all)
    assert not args.large_edge_cache or (args.pipeline and args.pipeline_direct and (not args.clip_edges or args.fast_left_clip))
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
    if args.staged_conversion:cfg=cfg.replace('CPUDATA: start=$2000, size=$DE00','CPUDATA: start=$2000, size=$8000')
    if args.offload_sort:
        cfg=cfg.replace('  IRAM:','  SA1JIT: start=$0700, size=$00F0, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  SA1SORT: load=BOOT, run=SA1JIT, type=ro, define=yes;')
    (BUILD/'game.cfg').write_text(cfg)
    ppu=bytearray((BASE/'assets4/ppu.bin').read_bytes())
    for y in range(24):
        for x in range(32):struct.pack_into('<H',ppu,0xc000+2*(y*32+x),(y*32+x)|0x2400)
    if args.native_far:
        from sa1_native_far import build as native_far
        ppu=native_far(ppu,(BASE/'assets4/background4.bin').read_bytes(),BUILD,dynamic=args.native_background)
    (BUILD/'ppu_sa1.bin').write_bytes(ppu)
    definitions=['FX_4BPP','FX_FULL_TRANSFER','FX_SMOOTH_DEPTH','FX_GSU_UV','FX_GSU_CLIP','FX_FAST_OBJ','FX_DYNAMIC_DMA','FX_FINE_DMA','FX_DESCRIPTOR_DMA','FX_GROUND_CACHE']
    defines=sum((['-D',s+'=1'] for s in definitions),[])+['-D','FX_DMA_ADMISSION_BYTES=9984']
    if args.wait_slots:defines+=['-D','SA1_WAIT_SLOTS=1']
    if args.front_delta:defines+=['-D','SA1_FRONT_DELTA=1']
    if args.native_background:defines+=['-D','SA1_NATIVE_BACKGROUND=1']
    if args.native_far:defines+=['-D','SA1_NATIVE_FAR=1']
    if args.staged_conversion:defines+=['-D','SA1_STAGED=1']
    if args.adaptive_vram:defines+=['-D','SA1_ADAPTIVE_VRAM=1']
    if args.prefill_pipeline:defines+=['-D','SA1_PREFILL=1']
    if args.skip_far_clear:defines+=['-D','SA1_SKIP_FAR_CLEAR=1']
    if args.linear_shape:defines+=['-D','SA1_LINEAR_SHAPE=1']
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
            if name=='ground' and args.staged_conversion:
                from sa1_pipeline_sources import rom_ground
                text=rom_ground(text)
            if name=='ground' and args.pipeline:
                from sa1_pipeline_sources import ground_buffers
                text=ground_buffers(text,args.pipeline_depth)
            src=BUILD/(name+'.s');src.write_text(text,encoding='utf-8')
        elif args.pipeline:
            from sa1_pipeline_sources import prepare
            generated=prepare(name,src.read_text(encoding='utf-8'),direct=args.pipeline_direct,irq=args.pipeline_irq,transfer_tiles=args.transfer_tiles,merge_dma=args.merge_dma,padded=args.padded_pipeline,large_edge=args.large_edge_cache,triple_bw=args.triple_bw,cpu_copy=args.cpu_code_copy,cpu_fill=args.cpu_fill,cpu_far=args.cpu_far)
            src=BUILD/(name+'_pipeline.s');src.write_text(generated,encoding='utf-8')
        if args.row_dirty and name in ('shape','dirty'):
            text=src.read_text(encoding='utf-8')
            if name=='shape':
                text=text.replace('  adc #7', '  adc #10')
                text=text.replace('  asl\n  asl\n  asl\n  sec\n  sbc shapeMid', '  asl\n  sta $f0\n  asl\n  asl\n  clc\n  adc $f0')
            else:
                text='.setcpu "65816"\n.import sa1_dirty_rows: far\n'+text
                text=text.replace('  lda f:$ff0003,x', '  lda dirty_width\n  and #255\n  cmp #32\n  bcc dirty_rows_small\n  lda dirty_height\n  cmp #24\n  bcc dirty_rows_small\n  jsl sa1_dirty_rows\n  rts\ndirty_rows_small:\n  lda f:$ff0003,x',1)
                text+='\n.export sa1_dirty_row_rect: far\n.segment "BOOT"\nsa1_dirty_row_rect:\n  jsr dirty_rect\n  rtl\n'
            src=BUILD/(name+'_row_dirty.s');src.write_text(text,encoding='utf-8')
        if args.native_far and name in ('cpu','dirty','renderer'):
            text=src.read_text(encoding='utf-8')
            if name=='cpu':
                text=text.replace('  stz $210b', '  lda #$60\n  sta $210b')
                text=text.replace('  lda #$7e\n  sta f:$00420c', '  lda #$fe\n  sta f:$00420c')
                text=text.replace('  sta $2107', '  sta $2107\n  lda #$61\n  sta $2108')
                text=text.replace('  lda #$13\n  sta f:$004371', '  lda #0\n  sta f:$004370\n  lda #$2c\n  sta f:$004371')
            if name=='renderer':
                text=text.replace('background:\n  rep #$30', 'background:\n  rep #$30\n  jmp bg_native_near')
                text=text.replace('  lda $010a\n  and #3', 'bg_native_near:\n  lda $010a\n  and #3')
            if name=='dirty':
                text=text.replace('  lda $0108\n  cmp $0110\n  bne dirty_background\n', '')
                text=text.replace('  adc #77\n  sta dirty_top', '  adc #82\n  sta dirty_top')
            if args.native_background:
                if name=='renderer':
                    text='.setcpu "65816"\n.import sa1_background_cache: far, sa1_background_initialize: far\n'+text
                    text=text.replace('background:\n  rep #$30\n  jmp bg_native_near', 'background:\n  rtl\n  rep #$30\n  jmp bg_native_near')
                    text=text.replace('finished:\nsa1_native_done:', 'finished:\n  jsl sa1_background_cache\nsa1_native_done:')
                    text=text.replace('wait_job:\n','  jsl sa1_background_initialize\nwait_job:\n',1)
                if name=='dirty':
                    text=text.replace('dirty_bg:\n', 'dirty_bg:\n  jmp dirty_save\n')
                    text=text.replace('  inc $0116\n', '  inc $0116\n  jmp dirty_return\n',1)
            src=BUILD/(name+'_native_far.s');src.write_text(text,encoding='utf-8')
        if args.adaptive_vram and name in ('dirty','renderer'):
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_adaptive_bounds: far, sa1_adaptive_prepare: far\n'+text
            if name=='dirty':text=text.replace('dirty_first:\n','dirty_first:\n  jsl sa1_adaptive_bounds\n')
            else:text=text.replace('  jsl sa1_prepare_transfer\n  jsl sa1_merge_dma', '  jsl sa1_adaptive_prepare')
            if args.front_delta:text=text.replace('sa1_adaptive_bounds','sa1_front_delta_bounds').replace('sa1_adaptive_prepare','sa1_front_delta_prepare')
            src=BUILD/(name+'_adaptive.s');src.write_text(text,encoding='utf-8')
        if name=='renderer' and args.offload_sort:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_sort_job: far\n'+text
            text=text.replace('  lda $0100\n  beq wait_job','  lda $0100\n  beq wait_job\n  cmp #2\n  bne sa1_clear_start\n  jsl sa1_sort_job\n  jmp wait_job')
            src=BUILD/'renderer_sort_job.s';src.write_text(text,encoding='utf-8')
        if name=='packet' and args.key_buckets:
            text=src.read_text(encoding='utf-8')
            text='.import sa1_key_buckets\n'+text
            text=text.replace('  sty packet_work+8                ; FX', '  sty packet_work+8\n  cpy #24\n  bcc :+\n  jsr sa1_key_buckets\n  bcc :+\n  jmp sorted\n:\n  ; FX')
            src=BUILD/'packet_key_buckets.s';src.write_text(text,encoding='utf-8')
        if name=='packet' and args.radix_sort:
            text=src.read_text(encoding='utf-8')
            text='.import sa1_radix_sort\n'+text
            text=text.replace('  sty packet_work+8                ; FX', '  sty packet_work+8\n  cpy #24\n  bcc :+\n  jsr sa1_radix_sort\n  jmp sorted\n:\n  ; FX')
            src=BUILD/'packet_radix.s';src.write_text(text,encoding='utf-8')
        if name=='packet' and args.offload_sort:
            text=src.read_text(encoding='utf-8')
            text='.import sa1_try_packet_sort\n'+text
            text=text.replace('  sty packet_work+8                ; FX', '  sty packet_work+8\n  jsr sa1_try_packet_sort\n  jcs sorted\n  ; FX')
            src=BUILD/'packet_sort_job.s';src.write_text(text,encoding='utf-8')
        if name=='cpu' and args.fastrom_cpu:
            text=src.read_text(encoding='utf-8').replace('  jml $7f0000 + game_started','  lda #1\n  sta f:$00420d\n  jml $c10000 + game_started')
            src=BUILD/'cpu_fastrom.s';src.write_text(text,encoding='utf-8')
        if name=='packet' and args.temporal_sort:
            text=src.read_text(encoding='utf-8')
            text='.import sa1_temporal_prepare, sa1_temporal_save\n'+text
            text=text.replace('  sty packet_work+8', '  sty packet_work+8\n  jsr sa1_temporal_prepare\n  ;')
            text=text.replace('  beq insert\n  sta keys+2,y', '  bne temporal_move\n  lda order,y\n  cmp packet_work+26\n  bcc insert\n  beq insert\n  lda keys,y\ntemporal_move:\n  sta keys+2,y')
            text=text.replace('sorted:\n', 'sorted:\n  jsr sa1_temporal_save\n')
            src=BUILD/'packet_temporal.s';src.write_text(text,encoding='utf-8')
        if name in ('dirty','renderer') and args.packet_shapes:
            from sa1_pipeline_sources import packet_shapes
            text=packet_shapes(name,src.read_text(encoding='utf-8'))
            src=BUILD/(name+'_packet_shapes.s');src.write_text(text,encoding='utf-8')
        if name=='edge' and args.cpu_edge_copy:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_edge_cpu_save: far, sa1_edge_cpu_restore: far\n'+text
            text=text.replace('  jsl sa1_dma_begin\nedge_save_line:', '  lda $011e\n  beq edge_save_dma\n  jsl sa1_edge_cpu_save\n  rtl\nedge_save_dma:\n  jsl sa1_dma_begin\nedge_save_line:')
            text=text.replace('  jsl sa1_dma_begin\nedge_restore_line:', '  lda $011e\n  beq edge_restore_dma\n  jsl sa1_edge_cpu_restore\n  rtl\nedge_restore_dma:\n  jsl sa1_dma_begin\nedge_restore_line:')
            src=BUILD/'edge_cpu.s';src.write_text(text,encoding='utf-8')
        if name=='renderer' and args.clip_edges:
            text=src.read_text(encoding='utf-8').replace('  lda $0120,x\n  sta dirtyL\n  lda $0122,x\n  sta dirtyR', '  lda #0\n  sta dirtyL\n  lda #128\n  sta dirtyR')
            text=text.replace('  lda dirtyL\n  cmp $b4', '  lda edge\n  jne row_partial\n  lda dirtyL\n  cmp $b4')
            if args.fast_left_clip:
                text='.setcpu "65816"\n.import sa1_clip_left_tail: far\n'+text
                text=text.replace('next:\n','next:\n  lda #$ffff\n  sta $ba\n')
                text=text.replace('  lda edge\n  jeq invoke_row', '  lda edge\n  jeq invoke_row\n  jsl sa1_clip_left_tail\n  jcs patched')
            src=BUILD/'renderer_clip_edges.s';src.write_text(text,encoding='utf-8')
        if name=='fast' and args.redraw_all:
            text=src.read_text(encoding='utf-8').replace('fast_tiles:\n','fast_tiles:\n  jmp fast_base_ready\n')
            if args.fast_left_clip:text=text.replace('  jsl sa1_edge_prepare\n','  jsl sa1_edge_prepare\n  lda $c4\n  beq fast_left_inside\n  lda $c0\n  and #255\n  clc\n  adc $38\n  bpl fast_left_inside\n  lda fright\n  cmp #33\n  jcc fast_fail\nfast_left_inside:\n')
            elif args.clip_edges:text=text.replace('  jsl sa1_edge_prepare\n','  jsl sa1_edge_prepare\n  lda $c4\n  jne fast_fail\n')
            src=BUILD/'fast_redraw_all.s';src.write_text(text,encoding='utf-8')
        if name=='renderer' and args.skip_far_clear:
            from sa1_pipeline_sources import skip_far_clear
            text=skip_far_clear(src.read_text(encoding='utf-8'))
            src=BUILD/'renderer_skip_far_clear.s';src.write_text(text,encoding='utf-8')
        obj=BUILD/(name+'_asm.o')
        run([CC/'ca65.exe',*defines,*(['-D','SA1_TILE_DMA=1'] if args.transfer_tiles and name=='dirty' else []),'-I',GAME,'-I',SA1,'-I',BASE,'-I',BUILD,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,src]);objs.append(obj)
    if args.pipeline:
        obj=BUILD/'pipeline_asm.o'
        run([CC/'ca65.exe',*defines,'-I',SA1,'-o',obj,SA1/'pipeline_sa1.s']);objs.append(obj)
    if args.row_dirty:
        obj=BUILD/'row_dirty.o';run([CC/'ca65.exe','-o',obj,SA1/'row_dirty_game.s']);objs.append(obj)
    if args.native_background:
        obj=BUILD/'background_cache.o';run([CC/'ca65.exe','-o',obj,SA1/'background_cache_sa1.s']);objs.append(obj)
    if args.key_buckets:
        obj=BUILD/'key_buckets.o';run([CC/'ca65.exe','-o',obj,SA1/'key_buckets_game.s']);objs.append(obj)
    if args.radix_sort:
        obj=BUILD/'radix_sort.o';run([CC/'ca65.exe','-o',obj,SA1/'radix_sort_game.s']);objs.append(obj)
    if args.adaptive_vram:
        obj=BUILD/'adaptive_vram.o';run([CC/'ca65.exe',*(['-D','SA1_NATIVE_BACKGROUND=1'] if args.native_background else []),*(['-D','SA1_FRONT_DELTA=1'] if args.front_delta else []),'-o',obj,SA1/'adaptive_vram_sa1.s']);objs.append(obj)
    if args.offload_sort:
        obj=BUILD/'sort_job.o';run([CC/'ca65.exe','-o',obj,SA1/'packet_sort_job.s']);objs.append(obj)
    if args.cpu_edge_copy:
        obj=BUILD/'edge_cpu.o';run([CC/'ca65.exe','-o',obj,SA1/'edge_cpu_game.s']);objs.append(obj)
    if args.fast_left_clip:
        obj=BUILD/'clip_left.o';run([CC/'ca65.exe','-o',obj,SA1/'clip_left_game.s']);objs.append(obj)
    if args.temporal_sort:
        obj=BUILD/'temporal_sort.o';run([CC/'ca65.exe','-o',obj,SA1/'temporal_sort_game.s']);objs.append(obj)
    if args.cpu_fill or args.cpu_far:
        obj=BUILD/'cpu_fill.o';run([CC/'ca65.exe','-o',obj,SA1/'cpu_fill_game.s']);objs.append(obj)
    if args.merge_dma:
        obj=BUILD/'merge_dma.o';run([CC/'ca65.exe','-o',obj,SA1/'merge_dma.s']);objs.append(obj)
    if args.staged_conversion:
        data=(BASE/'monosh_boss_data.s').read_text(encoding='utf-8')
        data=data.replace('_monosh_boss_draw_order_base:\n','.segment "BOOT"\n_monosh_boss_draw_order_base:\n').replace('_monosh_boss_face_geometry:\n','.segment "RODATA"\n_monosh_boss_face_geometry:\n')
        source=BUILD/'boss_data_rom.s';source.write_text(data,encoding='utf-8')
        obj=BUILD/'boss_data_rom.o';run([CC/'ca65.exe','-o',obj,source]);objs.append(obj)
    objs+=sorted(p for p in BASE.rglob('*.o') if p.name not in ('cpu_asm.o','ground_asm.o','objects_asm.o','packet_asm.o') and not (args.staged_conversion and p.name=='monosh_boss_data.o'))
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
        key=fingerprint.hexdigest()+args.renderer+str(stride)+str(args.row_dirty)+str(args.row_dirty_bands)
        suffix=('_256' if args.padded_pipeline else '')+('_rows' if args.row_dirty else '')+('_bands' if args.row_dirty_bands else '')
        cache=BUILD/('compiled_cache'+suffix+'.bin');metadata=BUILD/('compiled_cache'+suffix+'.json')
        if cache.exists() and metadata.exists() and json.loads(metadata.read_text()).get('key')==key:
            rom=bytearray(cache.read_bytes())
            (BUILD/'compiled_game_packing.json').write_text(json.dumps(json.loads(metadata.read_text())['packing'],indent=2)+'\n')
        else:
            rom=compiled_cache(variants,BUILD,macros=args.renderer=='macros',stride=stride,row_dirty=args.row_dirty,row_dirty_bands=args.row_dirty_bands)
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
    (BUILD/'manifest.json').write_text(json.dumps({'romSha256':hashlib.sha256(rom).hexdigest(),'sa1CodeBytes':labels['__SA1_SIZE__'],'renderer':args.renderer,'paddedFramebuffer':False,'directFramebuffer':args.renderer=='macros','tileDma':args.tile_dma,'bucketSort':args.bucket_sort,'pipeline':args.pipeline,'pipelineDirect':args.pipeline_direct,'pipelineIrq':args.pipeline_irq,'pipelineDepth':args.pipeline_depth,'transferTiles':args.transfer_tiles,'redrawAll':args.redraw_all,'mergeDma':args.merge_dma,'clipEdges':args.clip_edges,'paddedPipeline':args.padded_pipeline,'workingFramebufferStride':256 if args.padded_pipeline else 128,'largeEdgeCache':args.large_edge_cache,'tripleBw':args.triple_bw,'fastDma':args.fast_dma,'cpuCodeCopy':args.cpu_code_copy,'cpuFill':args.cpu_fill,'cpuFar':args.cpu_far,'shapeCache':args.shape_cache,'temporalSort':args.temporal_sort,'stagedConversion':args.staged_conversion,'fastLeftClip':args.fast_left_clip,'skipFarClear':args.skip_far_clear,'linearShape':args.linear_shape,'cpuEdgeCopy':args.cpu_edge_copy,'prefillPipeline':args.prefill_pipeline,'packetShapes':args.packet_shapes,'offloadSort':args.offload_sort,'adaptiveVram':args.adaptive_vram,'radixSort':args.radix_sort,'keyBuckets':args.key_buckets,'nativeFar':args.native_far,'nativeBackground':args.native_background,'frontDelta':args.front_delta,'rowDirty':args.row_dirty,'rowDirtyBands':args.row_dirty_bands,'waitSlots':args.wait_slots,'cpuCodeBank':0xc1 if args.fastrom_cpu else 0x7f,'stage':'dirty-tiles-two-pages','goal60fpsAchieved':False},indent=2)+'\n')
    print(path)

if __name__=='__main__':main()
