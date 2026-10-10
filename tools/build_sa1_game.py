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
    ap=argparse.ArgumentParser();ap.add_argument('--renderer',choices=['dma','shared','compiled','macros'],default='macros');ap.add_argument('--bucket-sort',action='store_true');ap.add_argument('--tile-dma',action='store_true');ap.add_argument('--pipeline',action='store_true');ap.add_argument('--pipeline-direct',action='store_true');ap.add_argument('--pipeline-irq',action='store_true');ap.add_argument('--stack-band',action='store_true');ap.add_argument('--stack-fill',action='store_true');ap.add_argument('--row-dirty-aligned',action='store_true');ap.add_argument('--visible-mask',action='store_true');ap.add_argument('--row-dirty-step',type=int,choices=[1,2,4,8,16],default=8);ap.add_argument('--changed-mask',action='store_true');ap.add_argument('--front-mask',action='store_true');ap.add_argument('--accurate-dma-budget',action='store_true');ap.add_argument('--occupancy',action='store_true');ap.add_argument('--wait-slots',action='store_true');ap.add_argument('--transfer-mask',action='store_true');ap.add_argument('--row-dirty-bands',action='store_true');ap.add_argument('--row-dirty',action='store_true');ap.add_argument('--front-delta',action='store_true');ap.add_argument('--native-background',action='store_true');ap.add_argument('--native-far',action='store_true');ap.add_argument('--key-buckets',action='store_true');ap.add_argument('--radix-sort',action='store_true');ap.add_argument('--adaptive-vram',action='store_true');ap.add_argument('--offload-sort',action='store_true');ap.add_argument('--fastrom-cpu',action='store_true');ap.add_argument('--packet-shapes',action='store_true');ap.add_argument('--prefill-pipeline',action='store_true');ap.add_argument('--cpu-edge-copy',action='store_true');ap.add_argument('--skip-far-clear',action='store_true');ap.add_argument('--linear-shape',action='store_true');ap.add_argument('--fast-left-clip',action='store_true');ap.add_argument('--staged-conversion',action='store_true');ap.add_argument('--temporal-sort',action='store_true');ap.add_argument('--shape-cache',action='store_true');ap.add_argument('--cpu-far',action='store_true');ap.add_argument('--cpu-fill',action='store_true');ap.add_argument('--cpu-code-copy',action='store_true');ap.add_argument('--fast-dma',action='store_true');ap.add_argument('--triple-bw',action='store_true');ap.add_argument('--large-edge-cache',action='store_true');ap.add_argument('--padded-pipeline',action='store_true');ap.add_argument('--clip-edges',action='store_true');ap.add_argument('--merge-dma',action='store_true');ap.add_argument('--redraw-all',action='store_true');ap.add_argument('--transfer-tiles',action='store_true');ap.add_argument('--pipeline-depth',type=int,choices=[3,4,5,8],default=3);ap.add_argument('--deep-bw',action='store_true');ap.add_argument('--prefill-count',type=int,choices=range(1,8),default=3);ap.add_argument('--native-near',action='store_true');ap.add_argument('--early-request',action='store_true');ap.add_argument('--bitset-sort',action='store_true');ap.add_argument('--list-sort',action='store_true');ap.add_argument('--small-edge-jit',action='store_true');ap.add_argument('--compiled-ground',action='store_true');ap.add_argument('--unroll-ppu-dma',action='store_true');ap.add_argument('--wide-clear',action='store_true');ap.add_argument('--bullet-cache',action='store_true');ap.add_argument('--bullet-words',action='store_true');ap.add_argument('--dense-tiles',action='store_true');ap.add_argument('--row-dirty-exact',action='store_true')
    ap.add_argument('--bottom-slack',action='store_true')
    ap.add_argument('--irq-fastrom',action='store_true')
    ap.add_argument('--dirty-iram',action='store_true')
    ap.add_argument('--cpu-pack',action='store_true')
    ap.add_argument('--wide-clear-min',type=int,default=104,choices=range(32,129,8))
    ap.add_argument('--left-hints',action='store_true')
    ap.add_argument('--right-clip-jit',action='store_true')
    ap.add_argument('--fallback-mask',action='store_true')
    ap.add_argument('--fallback-early',action='store_true')
    ap.add_argument('--fallback-sa1',action='store_true')
    ap.add_argument('--pixel-delta',action='store_true')
    ap.add_argument('--pixel-delta-min',type=int,default=9000)
    ap.add_argument('--vram-prefetch3',action='store_true')
    ap.add_argument('--vram-pump',action='store_true')
    ap.add_argument('--defer-stage',action='store_true')
    ap.add_argument('--late-flip',action='store_true')
    ap.add_argument('--sa1-game',action='store_true')
    ap.add_argument('--compact-memory',action='store_true')
    ap.add_argument('--sa1-game-compact',action='store_true')
    ap.add_argument('--game-irq-wram',action='store_true')
    ap.add_argument('--game-wait-wai',action='store_true')
    ap.add_argument('--split-map-dma',action='store_true')
    ap.add_argument('--split-map-mvn',action='store_true')
    ap.add_argument('--game-stage-overlap',action='store_true')
    ap.add_argument('--direct-sparse',action='store_true')
    ap.add_argument('--prefix-dma',action='store_true')
    ap.add_argument('--prefix-fastrom',action='store_true')
    ap.add_argument('--map-dma-overlap',action='store_true')
    ap.add_argument('--prefix-table',action='store_true')
    ap.add_argument('--sparse-merge-gap',type=int,choices=range(0,1025,32),default=0)
    ap.add_argument('--idle-clear',action='store_true')
    ap.add_argument('--bullet-left-fast',action='store_true')
    ap.add_argument('--bullet-opacity',action='store_true')
    ap.add_argument('--contiguous-chr-dma',action='store_true')
    ap.add_argument('--prefix-cpu-table',action='store_true')
    args=ap.parse_args()
    assert not args.split_map_mvn or args.split_map_dma
    assert not args.split_map_dma or (args.direct_sparse and args.prefix_fastrom and args.contiguous_chr_dma and args.native_near and not args.sa1_game and not args.sa1_game_compact)
    if args.sa1_game_compact:args.compact_memory=True
    assert not args.game_irq_wram or args.sa1_game_compact
    assert not args.game_wait_wai or args.sa1_game_compact
    assert not args.sa1_game_compact or (args.irq_fastrom and not args.fallback_sa1)
    assert not args.compact_memory or (args.deep_bw and args.compiled_ground and args.bullet_words and args.direct_sparse and args.stack_band and args.native_near and not args.sa1_game)
    assert not args.sa1_game or (args.deep_bw and args.irq_fastrom and not args.fallback_sa1 and args.prefill_count<=5)
    assert not args.game_stage_overlap or (args.sa1_game and args.cpu_pack)
    assert not args.direct_sparse or (args.vram_prefetch3 and not args.cpu_pack and not args.dense_tiles)
    assert not args.prefix_dma or (args.direct_sparse and args.unroll_ppu_dma)
    assert not args.prefix_fastrom or args.prefix_dma
    assert not args.map_dma_overlap or args.direct_sparse
    assert not args.prefix_table or args.prefix_fastrom
    assert not args.sparse_merge_gap or args.direct_sparse
    assert not args.idle_clear or (args.direct_sparse and args.compiled_ground and not args.sa1_game)
    assert not args.bullet_left_fast or args.bullet_words
    assert not args.bullet_opacity or args.bullet_words
    assert not args.contiguous_chr_dma or args.prefix_fastrom
    assert not args.prefix_cpu_table or (args.prefix_fastrom and not args.prefix_table)
    assert not args.cpu_pack or (args.deep_bw and args.bullet_words and args.irq_fastrom and not args.dense_tiles)
    if args.cpu_pack:args.staged_conversion=True
    assert not args.left_hints or (args.deep_bw and args.bullet_words)
    assert not args.right_clip_jit or (args.deep_bw and args.bullet_words)
    assert not args.fallback_mask or (args.deep_bw and args.irq_fastrom and not args.cpu_pack and not args.dense_tiles)
    assert not args.fallback_early or (args.fallback_mask and args.early_request)
    assert not args.fallback_sa1 or args.fallback_mask
    assert not args.pixel_delta or (args.deep_bw and args.front_mask and not args.cpu_pack and not args.dense_tiles)
    assert not args.vram_prefetch3 or ((args.dense_tiles or args.cpu_pack or args.direct_sparse) and args.irq_fastrom and args.deep_bw and args.native_near)
    assert not args.vram_pump or (args.vram_prefetch3 and args.cpu_pack)
    assert not args.defer_stage or (args.vram_prefetch3 and args.cpu_pack)
    assert not args.late_flip or args.vram_pump
    assert not args.row_dirty_exact or args.row_dirty_aligned
    assert not args.dirty_iram or (args.deep_bw and args.row_dirty_aligned)
    assert not args.irq_fastrom or args.pipeline
    assert not args.dense_tiles or (args.bullet_words and not args.unroll_ppu_dma)
    assert not args.bullet_words or args.bullet_cache
    assert not args.bullet_cache or (args.deep_bw and args.native_near and args.packet_shapes)
    assert not args.wide_clear or (args.stack_band and args.compiled_ground)
    assert not args.unroll_ppu_dma or (args.fast_dma and args.accurate_dma_budget and not args.fastrom_cpu)
    assert not args.compiled_ground or args.deep_bw
    assert not args.small_edge_jit or (args.cpu_edge_copy and args.large_edge_cache)
    assert not args.list_sort or (args.pipeline and not args.bitset_sort and not args.key_buckets and not args.radix_sort and not args.temporal_sort and not args.offload_sort)
    assert not args.bitset_sort or (args.pipeline and not args.key_buckets and not args.radix_sort and not args.temporal_sort and not args.offload_sort)
    assert not args.early_request or (args.pipeline_irq and (not args.staged_conversion or args.cpu_pack))
    assert not args.native_near or (args.deep_bw and args.visible_mask)
    assert not args.deep_bw or (args.pipeline_depth==8 and args.occupancy and args.front_mask)
    assert not args.stack_band or (args.pipeline_irq and args.native_background and not args.cpu_fill and not args.stack_fill)
    if args.stack_fill:args.cpu_fill=True
    assert not args.row_dirty_aligned or args.row_dirty
    assert not args.visible_mask or args.transfer_mask
    assert not args.changed_mask or args.front_mask
    assert not args.front_mask or (args.transfer_mask and args.occupancy and args.accurate_dma_budget)
    assert not args.accurate_dma_budget or (args.pipeline and args.fast_dma and (not args.staged_conversion or args.cpu_pack))
    assert not args.occupancy or (args.native_background and args.triple_bw and not args.adaptive_vram and not args.front_delta)
    assert not args.transfer_mask or (args.native_background and not args.adaptive_vram and not args.front_delta)
    assert not args.wait_slots or args.pipeline_irq
    assert not args.row_dirty_bands or args.row_dirty
    assert not args.row_dirty or (args.pipeline_direct and args.renderer=='macros' and not args.transfer_tiles)
    if args.front_delta:
        assert args.native_background
        args.adaptive_vram=True
    if args.native_background:args.native_far=True
    assert not args.native_far or (args.pipeline_direct and not args.skip_far_clear and (not args.fastrom_cpu or (args.irq_fastrom and args.cpu_pack)))
    assert not args.key_buckets or (args.pipeline and not args.radix_sort and not args.temporal_sort and not args.offload_sort)
    assert not args.radix_sort or (args.pipeline and not args.temporal_sort and not args.offload_sort)
    assert not args.adaptive_vram or (args.pipeline_direct and args.triple_bw and args.fast_dma and args.merge_dma and not args.staged_conversion and not args.transfer_tiles)
    assert not args.offload_sort or (args.pipeline_irq and args.large_edge_cache and not args.staged_conversion and not args.fastrom_cpu and not args.temporal_sort)
    assert not args.packet_shapes or (args.pipeline and args.renderer=='macros')
    assert not args.prefill_pipeline or (args.triple_bw and (args.pipeline_depth==5 or args.deep_bw))
    assert args.prefill_count<= (7 if args.deep_bw else 3)
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
    if args.left_hints:(BUILD/'left_hints.inc').write_text('LEFT_HINT_TABLE=$000000\nLEFT_HINT_MASK=8191\n',encoding='utf-8')
    variants=assets()
    if args.renderer=='macros':
        from sa1_flip_bullets import build as flip_build
        flip_build(variants,BUILD)
    cfg=(GAME/'rom.cfg').read_text()
    cfg=re.sub(r'start=\$([45][0-9A-F])([0-9A-F]{4})',lambda m:'start=$'+f'{int(m[1],16)+0x80:02X}'+m[2],cfg)
    cfg=cfg.replace('  CPUCODE:', '  IRAM: start=$0200, size=$05C0, file="";\n  CPUCODE:')
    cfg=cfg.replace('  BOOT: load=BOOT, type=ro;', '  BOOT: load=BOOT, type=ro;\n  SA1: load=BOOT, run=IRAM, type=ro, define=yes;')
    if args.staged_conversion or args.deep_bw:cfg=cfg.replace('CPUDATA: start=$2000, size=$DE00','CPUDATA: start=$2000, size=$8000')
    if args.deep_bw:cfg=cfg.replace('COLORRAM: start=$0400, size=$1200','COLORRAM: start=$A000, size=$5E00')
    if args.compact_memory:
        from sa1_compact_memory import configuration
        cfg=configuration(cfg)
    if args.fallback_mask:
        cfg=cfg.replace('  SPAN5F:', '  FALLBACKCPU: load=DATALOAD, type=ro, define=yes;\n  SPAN5F:')
    assert not args.bottom_slack or (args.deep_bw and args.bullet_words)
    if args.right_clip_jit:
        cfg=cfg.replace('  IRAM:', '  RIGHTRUN: start=$0300, size=$0200, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  RIGHTJIT: load=GSU, run=RIGHTRUN, type=ro, define=yes;')
    if args.left_hints:
        cfg=cfg.replace('  IRAM:', '  LEFTRUN: start=$0300, size=$0400, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  LEFTJIT: load=GSU, run=LEFTRUN, type=ro, define=yes;')
    if args.dirty_iram:
        cfg=cfg.replace('  IRAM:', '  DIRTYRUN: start=$0300, size=$0300, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  DIRTYJIT: load=GSU, run=DIRTYRUN, type=ro, define=yes;')
    if args.dense_tiles:
        cfg=cfg.replace('  IRAM:', '  DENSERUN: start=$0300, size=$0400, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  DENSEJIT: load=GSU, run=DENSERUN, type=ro, define=yes;')
    if args.bullet_cache:
        cfg=cfg.replace('  IRAM:', '  BULLETRUN: start=$0300, size=$0400, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  BULLETJIT: load=GSU, run=BULLETRUN, type=ro, define=yes;')
    if args.offload_sort:
        cfg=cfg.replace('  IRAM:','  SA1JIT: start=$0700, size=$00F0, file="";\n  IRAM:')
        cfg=cfg.replace('  SA1: load=BOOT, run=IRAM, type=ro, define=yes;', '  SA1: load=BOOT, run=IRAM, type=ro, define=yes;\n  SA1SORT: load=BOOT, run=SA1JIT, type=ro, define=yes;')
    (BUILD/'game.cfg').write_text(cfg)
    ppu=bytearray((BASE/'assets4/ppu.bin').read_bytes())
    for y in range(24):
        for x in range(32):struct.pack_into('<H',ppu,0xc000+2*(y*32+x),(y*32+x)|0x2400)
    if args.native_far:
        from sa1_native_far import build as native_far
        ppu=native_far(ppu,(BASE/'assets4/background4.bin').read_bytes(),BUILD,dynamic=args.native_background and not args.native_near)
        if args.native_near:
            from sa1_native_near import build as native_near
            ppu=native_near(ppu,(BASE/'assets4/background4.bin').read_bytes(),BUILD)
    if args.vram_prefetch3:
        from sa1_vram_prefetch import ppu_layout
        ppu=ppu_layout(ppu,BUILD)
    (BUILD/'ppu_sa1.bin').write_bytes(ppu)
    definitions=['FX_4BPP','FX_FULL_TRANSFER','FX_SMOOTH_DEPTH','FX_GSU_UV','FX_GSU_CLIP','FX_FAST_OBJ','FX_DYNAMIC_DMA','FX_FINE_DMA','FX_DESCRIPTOR_DMA','FX_GROUND_CACHE']
    defines=sum((['-D',s+'=1'] for s in definitions),[])+['-D','FX_DMA_ADMISSION_BYTES=9984']
    defines+=['-D',f'SA1_PREFILL_COUNT={args.prefill_count}']
    if args.game_wait_wai:defines+=['-D','SA1_GAME_WAIT_WAI=1']
    if args.game_stage_overlap:defines+=['-D','SA1_GAME_STAGE_OVERLAP=1']
    if args.irq_fastrom:defines+=['-D','SA1_IRQ_FASTROM=1']
    if args.vram_pump:defines+=['-D','SA1_VRAM_PUMP=1']
    if args.late_flip:defines+=['-D','SA1_LATE_FLIP=1']
    if args.deep_bw:defines+=['-D','SA1_DEEP_BW=1']
    if args.dense_tiles:
        from sa1_dense import pipeline as dense_pipeline
        text=dense_pipeline((SA1/'pipeline_cpu.inc').read_text(encoding='utf-8'))
        if args.vram_prefetch3:
            from sa1_vram_prefetch import pipeline as vram_pipeline
            text=vram_pipeline(text)
        (BUILD/'pipeline_dense.inc').write_text(text,encoding='utf-8')
    if args.cpu_pack:
        from sa1_cpu_pack import pipeline as cpu_pack_pipeline
        text=cpu_pack_pipeline((SA1/'pipeline_cpu.inc').read_text(encoding='utf-8'))
        if args.vram_prefetch3:
            from sa1_vram_prefetch import pipeline as vram_pipeline, cpu_stage
            text=vram_pipeline(text,pump=args.vram_pump,defer=args.defer_stage,late_flip=args.late_flip).replace('.include "cpu_pack_stage.inc"','.include "cpu_pack_stage_vram3.inc"')
            (BUILD/'cpu_pack_stage_vram3.inc').write_text(cpu_stage((SA1/'cpu_pack_stage.inc').read_text(encoding='utf-8'),pump=args.vram_pump),encoding='utf-8')
            if args.game_stage_overlap:
                path=BUILD/'cpu_pack_stage_vram3.inc';stage=path.read_text(encoding='utf-8')
                old='  lda #0\n  sta f:$00311c\n  lda #1\n  sta f:$00311e\n'
                assert stage.count(old)==1
                stage=stage.replace(old,'  lda f:$0031a0\n  bne :+\n  lda #0\n  sta f:$00311c\n:\n  lda #1\n  sta f:$00311e\n',1)
                path.write_text(stage,encoding='utf-8')
        (BUILD/'pipeline_dense.inc').write_text(text,encoding='utf-8')
    if args.fallback_mask:
        from sa1_fallback_mask import pipeline as fallback_pipeline
        (BUILD/'pipeline_fallback.inc').write_text(fallback_pipeline((SA1/'pipeline_cpu.inc').read_text(encoding='utf-8'),early=args.fallback_early),encoding='utf-8')
    if args.direct_sparse:
        from sa1_sparse_direct import pipeline as sparse_direct_pipeline
        text=sparse_direct_pipeline((SA1/'pipeline_cpu.inc').read_text(encoding='utf-8'),prefix=args.prefix_dma,prefix_fastrom=args.prefix_fastrom,map_overlap=args.map_dma_overlap,contiguous=args.contiguous_chr_dma)
        if args.idle_clear:
            from sa1_idle_clear import pipeline as idle_pipeline
            text=idle_pipeline(text)
        if args.prefix_table or args.prefix_cpu_table:
            text='.import sd_collect_costs: far\n'+text
            text=text.replace('pipe_collect_adaptive:\n','  jsl sd_collect_costs\npipe_collect_adaptive:\n')
        if args.split_map_dma:
            from sa1_split_map import pipeline as split_pipeline
            text=split_pipeline(text)
        (BUILD/'pipeline_dense.inc').write_text(text,encoding='utf-8')
    if args.irq_fastrom:
        source=BUILD/'pipeline_fallback.inc' if args.fallback_mask else BUILD/'pipeline_dense.inc' if args.dense_tiles or args.cpu_pack or args.direct_sparse else SA1/'pipeline_cpu.inc'
        text=source.read_text(encoding='utf-8').replace('jml $7f0000+pipe_irq','jml $c10000+pipe_irq')
        if args.sa1_game:
            from sa1_game_offload import cpu_pipeline
            text=cpu_pipeline(text)
        if args.sa1_game_compact:
            assert text.count('  lda #283\n')==1
            text=text.replace('  lda #283\n','  lda #279\n')
        if args.game_irq_wram:text=text.replace('$c10000+','$7f0000+')
        (BUILD/'pipeline_tuned.inc').write_text(text,encoding='utf-8')
    if args.native_near:defines+=['-D','SA1_NATIVE_NEAR=1']
    if args.changed_mask:defines+=['-D','SA1_CHANGED_MASK=1']
    if args.front_mask:defines+=['-D','SA1_FRONT_MASK=1']
    if args.accurate_dma_budget:defines+=['-D','SA1_ACCURATE_DMA_BUDGET=1']
    if args.occupancy:defines+=['-D','SA1_OCCUPANCY=1']
    if args.transfer_mask:defines+=['-D','SA1_TRANSFER_MASK=1']
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
    if args.early_request:defines+=['-D','SA1_EARLY_REQUEST=1']
    if args.unroll_ppu_dma:defines+=['-D','SA1_UNROLL_PPU_DMA=1']
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
                text+='\n.export player4_next, player4_uploaded\n.import pipe_obj_pointer\n'
                text=text.replace('lda #fx_obj_present+128','lda pipe_obj_pointer\n  clc\n  adc #128').replace('lda #fx_obj_present','lda pipe_obj_pointer')
            if name=='ground' and args.pipeline:text='.import pipe_ground_wait\n'+text.replace('_fx_build_ground:\n','_fx_build_ground:\n  jsr pipe_ground_wait\n')
            if name=='ground' and (args.staged_conversion or args.deep_bw):
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
        if args.transfer_mask and name in ('dirty','renderer'):
            text=src.read_text(encoding='utf-8')
            if name=='dirty':
                text='.setcpu "65816"\n.import sa1_tile_masks\n.import sa1_transfer_mask_capture: far\n'+text
                text=text.replace('dirty_init:\n','dirty_init:\n  lda #0\n  sta f:$436800,x\n  sta f:$436802,x\n')
                start=text.index('  .ifdef SA1_TILE_DMA\n  phx',text.index('dirty_rect:'))
                end=text.index('  .endif',start)+len('  .endif')
                text=text[:start]+text[start:end].replace('.ifdef SA1_TILE_DMA','.ifdef SA1_TRANSFER_MASK')+'\n'+text[start:]
                mask_code='  lda f:$436800,x\n  ora $bc\n  sta f:$436800,x\n  lda f:$436802,x\n  ora $be\n  sta f:$436802,x\n'
                if args.changed_mask:mask_code='  lda $b6\n  beq mask_mark_done\n'+mask_code+'mask_mark_done:\n'
                text=text.replace('dirty_rect_row:\n', 'dirty_rect_row:\n'+mask_code)
                text=text.replace('dirty_first:\n','dirty_first:\n  jsl sa1_transfer_mask_capture\n')
            else:
                text='.setcpu "65816"\n.import sa1_transfer_mask_prepare: far\n'+text
                text=text.replace('  jsl sa1_prepare_transfer\n  jsl sa1_merge_dma','  jsl sa1_transfer_mask_prepare')
            src=BUILD/(name+'_transfer_mask.s');src.write_text(text,encoding='utf-8')
        if args.renderer=='macros' and name in ('renderer','dirty','fast'):
            if args.bullet_cache:
                from sa1_bullet_cache import transform as flip_transform
            else:
                from sa1_flip_bullets import transform as flip_transform
            text=flip_transform(name,src.read_text(encoding='utf-8'))
            if args.bullet_words and name=='renderer':
                text=text.replace('  bcs cache_rows_ready', '  jcs skip')
            src=BUILD/(name+'_flip_bullets.s');src.write_text(text,encoding='utf-8')
        if args.stack_band and name=='renderer':
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_stack_clear_band: far, sa1_stack_clear_prepare: far, sa1_dma_try_begin: far\n'+text
            text=text.replace('  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\nclear_scanline:', '  jsl sa1_dma_try_begin\n  bcs clear_band_dma\n  jsl sa1_stack_clear_band\n  jmp clear_band_finished\nclear_band_dma:\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\nclear_scanline:',1)
            text=text.replace('clear_tile_next:\n  jsl sa1_dma_end\n','clear_tile_next:\n  jsl sa1_dma_end\nclear_band_finished:\n',1)
            text=text.replace('  stz bgrow\nclear_tile_row:', '  jsl sa1_stack_clear_prepare\n  stz bgrow\nclear_tile_row:',1)
            if args.wide_clear:
                text='.import sa1_clear_wide_band: far\n'+text
                text=text.replace('clear_band_dma:\n', 'clear_band_wide:\n  jsl sa1_clear_wide_band\n  jmp clear_tile_next\nclear_band_dma:\n',1)
                text=text.replace('  bcs clear_band_dma', f'  bcc :+\n  lda bgfirst\n  cmp #{args.wide_clear_min}\n  bcs clear_band_wide\n  bra clear_band_dma\n:',1)
                text=text.replace('  bne clear_tile_row','  jne clear_tile_row')
            src=BUILD/'renderer_stack_band.s';src.write_text(text,encoding='utf-8')
        if args.stack_fill and name=='renderer':
            text=src.read_text(encoding='utf-8').replace('sa1_cpu_clear_line','sa1_stack_clear_line')
            src=BUILD/'renderer_stack_fill.s';src.write_text(text,encoding='utf-8')
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
        if args.occupancy and name in ('dirty','renderer'):
            text=src.read_text(encoding='utf-8')
            if name=='dirty':
                text='.setcpu "65816"\n.import sa1_occupancy_capture: far\n'+text
                a=text.index('dirty_compare:\n');b=text.index('dirty_bg:\n',a)
                text=text[:a]+"dirty_compare:\n  lda dirty_i\n  cmp dirty_count\n  jcs dirty_bg\n  phx\n  stz dirty_ptr\n  jsr dirty_mark\n  plx\ndirty_next:\n  txa\n  clc\n  adc #10\n  tax\n  inc dirty_i\n  jmp dirty_compare\n"+text[b:]
                if args.changed_mask:
                    a=text.index('dirty_compare:\n');b=text.index('dirty_bg:\n',a)
                    compare="dirty_compare:\n  lda dirty_i\n  cmp dirty_max\n  jcs dirty_bg\n  lda #1\n  sta $b6\n  lda dirty_i\n  cmp dirty_count\n  bcs changed_mask_mark\n  cmp $010e\n  bcs changed_mask_mark\n"
                    for offset in (0,2,4,6):compare+=f'  lda f:${0x430000+offset:06x},x\n  cmp f:${0x431000+offset:06x},x\n  bne changed_mask_mark\n'
                    compare+='  stz $b6\nchanged_mask_mark:\n  phx\n  lda dirty_i\n  cmp dirty_count\n  bcs changed_mask_old\n  stz dirty_ptr\n  jsr dirty_mark\nchanged_mask_old:\n  plx\n  phx\n  lda $b6\n  beq changed_mask_next\n  lda dirty_i\n  cmp $010e\n  bcs changed_mask_next\n  lda #$1000\n  sta dirty_ptr\n  jsr dirty_mark\nchanged_mask_next:\n  plx\ndirty_next:\n  txa\n  clc\n  adc #10\n  tax\n  inc dirty_i\n  jmp dirty_compare\n'
                    text=text[:a]+compare+text[b:]
                a=text.index('pipeline_merge:\n');b=text.index('  rtl',a)+len('  rtl')
                text=text[:a]+'pipeline_merge:\n  jsl sa1_occupancy_capture\n  rtl'+text[b:]
            else:
                text=text.replace('  lda $0120,x\n  sta dirtyL\n  lda $0122,x\n  sta dirtyR','  lda #0\n  sta dirtyL\n  lda #128\n  sta dirtyR')
            src=BUILD/(name+'_occupancy.s');src.write_text(text,encoding='utf-8')
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
        if name=='packet' and (args.key_buckets or args.bitset_sort):
            text=src.read_text(encoding='utf-8')
            text='.import sa1_key_buckets\n'+text
            text=text.replace('  sty packet_work+8                ; FX', '  sty packet_work+8\n  cpy #24\n  bcc :+\n  jsr sa1_key_buckets\n  bcc :+\n  jmp sorted\n:\n  ; FX')
            src=BUILD/'packet_key_buckets.s';src.write_text(text,encoding='utf-8')
        if name=='packet' and args.list_sort:
            text=src.read_text(encoding='utf-8')
            text='.import sa1_list_sort\n'+text
            text=text.replace('  sty packet_work+8                ; FX', '  sty packet_work+8\n  cpy #24\n  bcc :+\n  jsr sa1_list_sort\n  jmp sorted\n:\n  ; FX')
            src=BUILD/'packet_list.s';src.write_text(text,encoding='utf-8')
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
            text=text.replace('  jsl sa1_dma_begin\nedge_save_line:', '  lda $c4\n  cmp #9\n  bcc edge_save_cpu\n  lda $011e\n  beq edge_save_dma\nedge_save_cpu:\n  jsl sa1_edge_cpu_save\n  rtl\nedge_save_dma:\n  jsl sa1_dma_begin\nedge_save_line:')
            text=text.replace('  jsl sa1_dma_begin\nedge_restore_line:', '  lda $c4\n  cmp #9\n  bcc edge_restore_cpu\n  lda $011e\n  beq edge_restore_dma\nedge_restore_cpu:\n  jsl sa1_edge_cpu_restore\n  rtl\nedge_restore_dma:\n  jsl sa1_dma_begin\nedge_restore_line:')
            src=BUILD/'edge_cpu.s';src.write_text(text,encoding='utf-8')
        if name=='edge' and args.small_edge_jit:
            from sa1_small_edges import build as small_build, transform as small_transform
            small_build(BUILD)
            text=small_transform(src.read_text(encoding='utf-8'))
            src=BUILD/'edge_small.s';src.write_text(text,encoding='utf-8')
        if name=='ground' and args.compiled_ground:
            from sa1_ground_compiled import build as ground_compile, transform as ground_transform
            ground_compile(GAME/'assets',BUILD)
            text=ground_transform(src.read_text(encoding='utf-8'))
            src=BUILD/'ground_compiled.s';src.write_text(text,encoding='utf-8')
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
        if args.deep_bw:
            from sa1_deep_buffers import transform
            generated=transform(name,src.read_text(encoding='utf-8'))
            src=BUILD/(name+'_deep.s');src.write_text(generated,encoding='utf-8')
        if args.native_near:
            from sa1_native_near import transform as near_transform
            generated=near_transform(name,src.read_text(encoding='utf-8'))
            src=BUILD/(name+'_native_near.s');src.write_text(generated,encoding='utf-8')
        if name=='fast' and args.bottom_slack:
            text=src.read_text(encoding='utf-8')
            old='  lda flast\n  cmp $36\n  bne fast_chunks'
            new='  lda $3a\n  clc\n  adc $36\n  cmp #249\n  jcs fast_chunks'
            assert old in text
            src=BUILD/'fast_bottom_slack.s';src.write_text(text.replace(old,new,1),encoding='utf-8')
        if name=='fast' and args.left_hints:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_left_hint_draw: far\n'+text
            old='  jsl sa1_edge_prepare'
            new='''  jsl sa1_edge_prepare
  lda $c4
  beq left_hint_unavailable
  lda $38
  bpl left_hint_unavailable
  lda $34
  cmp #64
  bcc left_hint_unavailable
  lda $3e
  beq left_hint_available
  cmp #2
  beq left_hint_available
  cmp #3
  beq left_hint_available
  cmp #5
  bne left_hint_unavailable
left_hint_available:
  jsl sa1_left_hint_draw
  sec
  rtl
left_hint_unavailable:'''
            assert old in text
            src=BUILD/'fast_left_hints.s';src.write_text(text.replace(old,new,1),encoding='utf-8')
        if name=='fast' and args.right_clip_jit:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_right_clip_draw: far\n'+text
            old='  jsl sa1_edge_prepare'
            new='''  jsl sa1_edge_prepare
  lda $c4
  beq right_jit_unavailable
  lda $38
  bmi right_jit_unavailable
  jsl sa1_right_clip_draw
  sec
  rtl
right_jit_unavailable:'''
            assert text.count(old)==1
            src=BUILD/'fast_right_jit.s';src.write_text(text.replace(old,new,1),encoding='utf-8')
        if args.dirty_iram:
            from sa1_dirty_iram import transform as dirty_iram_transform
            text=dirty_iram_transform(name,src.read_text(encoding='utf-8'))
            src=BUILD/(name+'_dirty_iram.s');src.write_text(text,encoding='utf-8')
        if args.dense_tiles:
            from sa1_dense import transform as dense_transform
            text=dense_transform(name,src.read_text(encoding='utf-8'))
            src=BUILD/(name+'_dense.s');src.write_text(text,encoding='utf-8')
        if args.cpu_pack or args.direct_sparse:
            from sa1_cpu_pack import transform as cpu_pack_transform
            text=cpu_pack_transform(name,src.read_text(encoding='utf-8'))
            if name=='renderer' and args.direct_sparse:
                text='.setcpu "65816"\n.import sa1_sparse_direct_finish: far\n'+text
                text=text.replace('  jsl sa1_sparse_map_prepare\n','  jsl sa1_sparse_map_prepare\n  jsl sa1_sparse_direct_finish\n')
            src=BUILD/(name+'_cpu_pack.s');src.write_text(text,encoding='utf-8')
        if name=='cpu' and args.irq_fastrom:
            text=src.read_text(encoding='utf-8')
            text=text.replace('.include "pipeline_dense.inc"','.include "pipeline_tuned.inc"').replace('.include "pipeline_cpu.inc"','.include "pipeline_tuned.inc"')
            text=text.replace('  jml $7f0000 + game_started','  lda #1\n  sta f:$00420d\n  jml $7f0000 + game_started')
            src=BUILD/'cpu_irq_fastrom.s';src.write_text(text,encoding='utf-8')
        if name=='cpu' and args.fallback_mask:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import fallback_boot_clear: far\n'+text
            old='  mvn #$c2,#$7e'
            assert text.count(old)==1
            new='  mvn #$c2,#$7e\n  jsl fallback_boot_clear'
            src=BUILD/'cpu_fallback_boot.s';src.write_text(text.replace(old,new,1),encoding='utf-8')
        if name=='cpu' and args.vram_prefetch3:
            text=src.read_text(encoding='utf-8')
            old='  lda #$60\n  sta $2107\n'
            assert text.count(old)==1
            src=BUILD/'cpu_vram_prefetch.s';src.write_text(text.replace(old,'  lda #4\n  sta $2107\n',1),encoding='utf-8')
        if name=='renderer' and args.fallback_sa1:
            text=src.read_text(encoding='utf-8')
            old='  lda #0\n  tcd\n  stz $1e\n'
            assert text.count(old)==1
            src=BUILD/'renderer_fallback_sa1.s';src.write_text(text.replace(old,'  lda #0\n  tcd\n  sta f:$0001a0\n  stz $1e\n',1),encoding='utf-8')
        if name=='renderer' and (args.sa1_game or args.sa1_game_compact):
            text=src.read_text(encoding='utf-8')
            text=text.replace('  lda #0\n  tcd\n  stz $1e\n','  lda #0\n  tcd\n  sta f:$0001a0\n  sta f:$0001a2\n  stz $1e\n',1)
            text=text.replace('  lda #$80\n  sta $220a\n','  lda #1\n  sta f:$0001a2\n  lda #$80\n  sta $220a\n',1)
            src=BUILD/'renderer_sa1_game.s';src.write_text(text,encoding='utf-8')
        if name=='renderer' and args.pixel_delta:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_pixel_delta: far\n'+text
            old='  jsl sa1_transfer_mask_prepare\n'
            assert text.count(old)==1
            src=BUILD/'renderer_pixel_delta.s';src.write_text(text.replace(old,old+'  jsl sa1_pixel_delta\n',1),encoding='utf-8')
        if name=='renderer' and args.idle_clear:
            from sa1_idle_clear import renderer as idle_renderer
            text=idle_renderer(src.read_text(encoding='utf-8'))
            src=BUILD/'renderer_idle_clear.s';src.write_text(text,encoding='utf-8')
        if args.sa1_game_compact and name in ('packet','objects'):
            from sa1_compact_memory import game_source
            text=game_source(src.read_text(encoding='utf-8'))
            src=BUILD/(name+'_compact.s');src.write_text(text,encoding='utf-8')
        if name=='cpu' and args.sa1_game_compact:
            from sa1_compact_memory import math_source
            (BUILD/'math_compact.inc').write_text(math_source((GAME/'math4.inc').read_text(encoding='utf-8')),encoding='utf-8')
            text=src.read_text(encoding='utf-8').replace('.include "math4.inc"','.include "math_compact.inc"')
            src=BUILD/'cpu_compact_game.s';src.write_text(text,encoding='utf-8')
        if name=='cpu' and args.compact_memory:
            from sa1_compact_memory import cpu as compact_cpu
            text=compact_cpu(src.read_text(encoding='utf-8'))
            src=BUILD/'cpu_compact_memory.s';src.write_text(text,encoding='utf-8')
        if name=='renderer' and args.compact_memory:
            from sa1_compact_memory import renderer as compact_renderer
            text=compact_renderer(src.read_text(encoding='utf-8'))
            src=BUILD/'renderer_compact_memory.s';src.write_text(text,encoding='utf-8')
        obj=BUILD/(name+'_asm.o')
        run([CC/'ca65.exe',*defines,*(['-D','SA1_TILE_DMA=1'] if args.transfer_tiles and name=='dirty' else []),'-I',GAME,'-I',SA1,'-I',BASE,'-I',BUILD,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,src]);objs.append(obj)
    if args.compact_memory:
        obj=BUILD/'compact_ppu_boot.o';run([CC/'ca65.exe','-o',obj,SA1/'compact_ppu_boot.s']);objs.append(obj)
    if args.pipeline:
        obj=BUILD/'pipeline_asm.o'
        src=SA1/'pipeline_sa1.s'
        if args.sa1_game or args.sa1_game_compact:
            text='.setcpu "65816"\n.import sa1_game_irq: far\n'+src.read_text(encoding='utf-8')
            old='irq_no_dma:\n  rep #$30\n'
            assert text.count(old)==1
            src=BUILD/'pipeline_game_sa1.s';src.write_text(text.replace(old,old+'  jsl sa1_game_irq\n',1),encoding='utf-8')
        if args.fallback_sa1:
            text=src.read_text(encoding='utf-8')
            text='.setcpu "65816"\n.import sa1_fallback_irq: far\n'+text
            old='irq_no_dma:\n  rep #$30\n'
            assert text.count(old)==1
            src=BUILD/'pipeline_fallback_sa1.s';src.write_text(text.replace(old,old+'  jsl sa1_fallback_irq\n',1),encoding='utf-8')
        run([CC/'ca65.exe',*defines,'-I',SA1,'-o',obj,src]);objs.append(obj)
    if args.occupancy:
        source=SA1/'occupancy_game.s'
        if args.deep_bw:
            source=BUILD/'occupancy_deep.s';source.write_text(transform('occupancy',(SA1/'occupancy_game.s').read_text(encoding='utf-8')),encoding='utf-8')
        if args.sa1_game:
            from sa1_game_offload import five_slots
            source.write_text(five_slots('occupancy',source.read_text(encoding='utf-8')),encoding='utf-8')
        obj=BUILD/'occupancy.o';run([CC/'ca65.exe','-o',obj,source]);objs.append(obj)
    if args.transfer_mask:
        source=SA1/'transfer_mask_game.s'
        if args.deep_bw:
            source=BUILD/'transfer_mask_deep.s';source.write_text(transform('transfer_mask',(SA1/'transfer_mask_game.s').read_text(encoding='utf-8')),encoding='utf-8')
        if args.cpu_pack or args.direct_sparse:
            from sa1_cpu_pack import transform as cpu_pack_transform
            text=cpu_pack_transform('transfer_mask',source.read_text(encoding='utf-8'))
            if args.sparse_merge_gap:
                marker='sa1_transfer_mask_prepare:\n  rep #$30\n  lda #1\n'
                assert text.count(marker)==1
                text=text.replace(marker,marker.replace('lda #1',f'lda #{args.sparse_merge_gap+1}'),1)
            source=BUILD/'transfer_mask_cpu_pack.s';source.write_text(text,encoding='utf-8')
        obj=BUILD/'transfer_mask.o';run([CC/'ca65.exe',*(['-D','SA1_OCCUPANCY=1'] if args.occupancy and not args.front_mask else []),*(['-D','SA1_FRONT_MASK=1'] if args.front_mask else []),*(['-D','SA1_CHANGED_MASK=1'] if args.changed_mask else []),*(['-D','SA1_VISIBLE_MASK=1'] if args.visible_mask else []),'-o',obj,source]);objs.append(obj)
    if args.deep_bw:
        from sa1_deep_buffers import REBASE
        source=BUILD/'deep_rebase.s';source.write_text(REBASE,encoding='utf-8')
        obj=BUILD/'deep_rebase.o';run([CC/'ca65.exe','-o',obj,source]);objs.append(obj)
    if args.row_dirty:
        source=SA1/'row_dirty_game.s'
        if args.dirty_iram:
            from sa1_dirty_iram import transform as dirty_iram_transform
            text=dirty_iram_transform('row_dirty',source.read_text(encoding='utf-8'))
            source=BUILD/'row_dirty_iram.s';source.write_text(text,encoding='utf-8')
            obj=BUILD/'dirty_iram.o';run([CC/'ca65.exe','-o',obj,SA1/'dirty_iram_game.s']);objs.append(obj)
        obj=BUILD/'row_dirty.o';run([CC/'ca65.exe',*(['-D','SA1_ROW_DIRTY_ALIGNED=1'] if args.row_dirty_aligned else []),*(['-D','SA1_ROW_DIRTY_EXACT=1'] if args.row_dirty_exact else []),*(['-D','SA1_DEEP_BW=1'] if args.deep_bw else []),'-o',obj,source]);objs.append(obj)
    if args.native_background:
        source=SA1/'background_cache_sa1.s'
        if args.deep_bw:
            source=BUILD/'background_cache_deep.s';source.write_text(transform('background_cache',(SA1/'background_cache_sa1.s').read_text(encoding='utf-8')),encoding='utf-8')
        if args.sa1_game:
            from sa1_game_offload import five_slots
            source.write_text(five_slots('background_cache',source.read_text(encoding='utf-8')),encoding='utf-8')
        obj=BUILD/'background_cache.o';run([CC/'ca65.exe','-o',obj,source]);objs.append(obj)
    if args.native_near:
        for name in ('near_patch_game','near_obj_cpu'):
            obj=BUILD/(name+'.o');run([CC/'ca65.exe','--bin-include-dir',BUILD,'-o',obj,SA1/(name+'.s')]);objs.append(obj)
    if args.key_buckets or args.bitset_sort:
        obj=BUILD/'key_buckets.o';run([CC/'ca65.exe','-o',obj,SA1/('key_bitsets_game.s' if args.bitset_sort else 'key_buckets_game.s')]);objs.append(obj)
    if args.list_sort:
        source=SA1/'list_sort_game.s'
        if args.sa1_game_compact:
            source=BUILD/'list_sort_compact.s';source.write_text((SA1/'list_sort_game.s').read_text(encoding='utf-8').replace('.segment "COLORBSS"','.segment "BSS"'),encoding='utf-8')
        obj=BUILD/'list_sort.o';run([CC/'ca65.exe','-o',obj,source]);objs.append(obj)
    if args.radix_sort:
        obj=BUILD/'radix_sort.o';run([CC/'ca65.exe','-o',obj,SA1/'radix_sort_game.s']);objs.append(obj)
    if args.adaptive_vram:
        obj=BUILD/'adaptive_vram.o';run([CC/'ca65.exe',*(['-D','SA1_NATIVE_BACKGROUND=1'] if args.native_background else []),*(['-D','SA1_FRONT_DELTA=1'] if args.front_delta else []),'-o',obj,SA1/'adaptive_vram_sa1.s']);objs.append(obj)
    if args.offload_sort:
        obj=BUILD/'sort_job.o';run([CC/'ca65.exe','-o',obj,SA1/'packet_sort_job.s']);objs.append(obj)
    if args.cpu_edge_copy:
        obj=BUILD/'edge_cpu.o';run([CC/'ca65.exe','-o',obj,SA1/'edge_cpu_game.s']);objs.append(obj)
    if args.compiled_ground:
        src=SA1/'ground_compiled_cpu.s'
        if args.fallback_sa1 or args.vram_prefetch3:
            src=BUILD/'ground_compiled_gsu.s';src.write_text((SA1/'ground_compiled_cpu.s').read_text(encoding='utf-8').replace('.segment "BOOT"','.segment "GSU"'),encoding='utf-8')
        if args.compact_memory:
            from sa1_compact_memory import relocate_ground_pointers
            relocate_ground_pointers(BUILD)
        obj=BUILD/'ground_compiled.o';run([CC/'ca65.exe','--bin-include-dir',BUILD,'-o',obj,src]);objs.append(obj)
    if args.renderer=='macros':
        obj=BUILD/'flip_bullet.o';run([CC/'ca65.exe',*(['-D','SA1_BULLET_LEFT_FAST=1'] if args.bullet_left_fast else []),*(['-D','SA1_BULLET_OPACITY=1'] if args.bullet_opacity else []),'-I',BUILD,'--bin-include-dir',BUILD,'-o',obj,SA1/('bullet_words_game.s' if args.bullet_words else 'bullet_cache_game.s' if args.bullet_cache else 'flip_bullet_game.s')]);objs.append(obj)
    if args.dense_tiles:
        src=SA1/'dense_game.s'
        if args.vram_prefetch3:
            from sa1_vram_prefetch import dense as vram_dense
            src=BUILD/'dense_vram_prefetch.s';src.write_text(vram_dense((SA1/'dense_game.s').read_text(encoding='utf-8')),encoding='utf-8')
        obj=BUILD/'dense.o';run([CC/'ca65.exe','-o',obj,src]);objs.append(obj)
    if args.idle_clear:
        obj=BUILD/'idle_clear.o';run([CC/'ca65.exe','-o',obj,SA1/'idle_clear_sa1.s']);objs.append(obj)
    if args.cpu_pack or args.direct_sparse:
        src=SA1/'sparse_map_game.s'
        if args.vram_prefetch3:
            from sa1_vram_prefetch import sparse_map
            src=BUILD/'sparse_map_vram3.s';src.write_text(sparse_map((SA1/'sparse_map_game.s').read_text(encoding='utf-8')),encoding='utf-8')
        if args.split_map_dma:
            from sa1_split_map import source as split_source
            text=split_source(src.read_text(encoding='utf-8'),mvn=args.split_map_mvn)
            src=BUILD/'sparse_map_split.s';src.write_text(text,encoding='utf-8')
        obj=BUILD/'sparse_map.o';run([CC/'ca65.exe','-o',obj,src]);objs.append(obj)
    if args.split_map_dma:
        obj=BUILD/'split_map_cpu.o';run([CC/'ca65.exe','-o',obj,SA1/'split_map_cpu.s']);objs.append(obj)
    if args.direct_sparse:
            obj=BUILD/'sparse_direct.o';run([CC/'ca65.exe',*(['-D','SA1_PREFIX_TABLE=1'] if args.prefix_table else []),'-D',f'SA1_PREFIX_DESC_COST={52 if args.contiguous_chr_dma else 64}','-o',obj,SA1/'sparse_direct_game.s']);objs.append(obj)
            if args.prefix_dma:
                obj=BUILD/'prefix_dma.o';run([CC/'ca65.exe','-D',f'SA1_PREFIX_DESC_COST={52 if args.contiguous_chr_dma else 64 if args.prefix_fastrom else 76}',*(['-D','SA1_PREFIX_CPU_TABLE=1'] if args.prefix_cpu_table else []),'-o',obj,SA1/('prefix_table_cpu.s' if args.prefix_table or args.prefix_cpu_table else 'prefix_dma_cpu.s')]);objs.append(obj)
    if args.left_hints:
        obj=BUILD/'left_hints.o';run([CC/'ca65.exe','-I',BUILD,'-o',obj,SA1/'left_hints_game.s']);objs.append(obj)
    if args.right_clip_jit:
        obj=BUILD/'right_clip.o';run([CC/'ca65.exe','-o',obj,SA1/'right_clip_game.s']);objs.append(obj)
    if args.fallback_mask:
        src=SA1/'fallback_mask_cpu.s'
        if args.fallback_sa1:
            text=src.read_text(encoding='utf-8')
            begin=text.index('  lda #65\n  sta fbActive\n',text.index('fallback_prepare:'))
            src=BUILD/'fallback_mask_cpu_sa1.s';src.write_text(text[:begin]+(SA1/'fallback_mask_sa1_cpu.inc').read_text(encoding='utf-8'),encoding='utf-8')
            obj=BUILD/'fallback_mask_sa1.o';run([CC/'ca65.exe','-o',obj,SA1/'fallback_mask_sa1.s']);objs.append(obj)
        obj=BUILD/'fallback_mask.o';run([CC/'ca65.exe','-o',obj,src]);objs.append(obj)
    if args.pixel_delta:
        obj=BUILD/'pixel_delta.o';run([CC/'ca65.exe','-D',f'SA1_PIXEL_DELTA_MIN={args.pixel_delta_min}','-o',obj,SA1/'pixel_delta_game.s']);objs.append(obj)
    if args.small_edge_jit:
        obj=BUILD/'small_edge.o';run([CC/'ca65.exe','--bin-include-dir',BUILD,'-o',obj,SA1/'small_edge_game.s']);objs.append(obj)
    if args.fast_left_clip:
        obj=BUILD/'clip_left.o';run([CC/'ca65.exe','-o',obj,SA1/'clip_left_game.s']);objs.append(obj)
    if args.temporal_sort:
        obj=BUILD/'temporal_sort.o';run([CC/'ca65.exe','-o',obj,SA1/'temporal_sort_game.s']);objs.append(obj)
    if args.stack_fill or args.stack_band:
        obj=BUILD/'stack_fill.o';run([CC/'ca65.exe','-o',obj,SA1/'stack_fill_game.s']);objs.append(obj)
    if args.cpu_fill or args.cpu_far:
        obj=BUILD/'cpu_fill.o';run([CC/'ca65.exe','-o',obj,SA1/'cpu_fill_game.s']);objs.append(obj)
    if args.merge_dma:
        obj=BUILD/'merge_dma.o';run([CC/'ca65.exe','-o',obj,SA1/'merge_dma.s']);objs.append(obj)
    if args.staged_conversion or args.deep_bw:
        data=(BASE/'monosh_boss_data.s').read_text(encoding='utf-8')
        data=data.replace('_monosh_boss_draw_order_base:\n','.segment "BOOT"\n_monosh_boss_draw_order_base:\n').replace('_monosh_boss_face_geometry:\n','.segment "RODATA"\n_monosh_boss_face_geometry:\n')
        source=BUILD/'boss_data_rom.s';source.write_text(data,encoding='utf-8')
        obj=BUILD/'boss_data_rom.o';run([CC/'ca65.exe','-o',obj,source]);objs.append(obj)
    replaced=set()
    if args.sa1_game:
        from sa1_game_offload import frame
        for path in sorted(GAME.glob('*.s')):
            text=path.read_text(encoding='utf-8')
            if path.name=='frame.s':text=frame(text)
            elif 'f:$7f0000+' in text and path.name not in ('cpu.s','cpu4.s','ground.s','color.s'):
                text=text.replace('f:$7f0000+','f:$c10000+')
            else:continue
            source=BUILD/(path.stem+'_game_rom.s');source.write_text(text,encoding='utf-8')
            obj=BUILD/(path.stem+'_game_rom.o')
            run([CC/'ca65.exe',*defines,'-I',GAME,'-I',BASE,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,source])
            objs.append(obj);replaced.add(path.stem+'_asm.o')
        for name in ('game_cpu','game_sa1'):
            obj=BUILD/(name+'.o');run([CC/'ca65.exe',*defines,'-o',obj,SA1/(name+'.s')]);objs.append(obj)
    if args.sa1_game_compact:
        from sa1_game_offload import frame
        from sa1_compact_memory import game_source
        excluded={'cpu','cpu4','ground','audio','gsu','gsu4','objects','objects4','packet','color'}
        for path in sorted(GAME.glob('*.s')):
            if path.stem in excluded or not (BASE/(path.stem+'_asm.o')).exists():continue
            text=game_source(path.read_text(encoding='utf-8'))
            if path.stem=='frame':text=frame(text)
            source=BUILD/(path.stem+'_game_rom.s');source.write_text(text,encoding='utf-8')
            obj=BUILD/(path.stem+'_game_rom.o')
            run([CC/'ca65.exe',*defines,'-I',GAME,'-I',BASE,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,source])
            objs.append(obj);replaced.add(path.stem+'_asm.o')
        text=(GAME/'audio.s').read_text(encoding='utf-8').replace('_fx_audio_events: .res 1','.segment "BSS"\n_fx_audio_events: .res 1').replace('audio_old_player:','.segment "AUDIOBSS"\naudio_old_player:',1)
        source=BUILD/'audio_compact.s';source.write_text(text,encoding='utf-8')
        obj=BUILD/'audio_compact.o';run([CC/'ca65.exe',*defines,'-I',GAME,'-I',BASE,'--bin-include-dir',GAME,'--bin-include-dir',BASE,'-o',obj,source]);objs.append(obj);replaced.add('audio_asm.o')
        for name in ('cpu','sa1'):
            obj=BUILD/('game_'+name+'.o');run([CC/'ca65.exe',*defines,'-o',obj,SA1/('game_compact_'+name+'.s')]);objs.append(obj)
    objs+=sorted(p for p in BASE.rglob('*.o') if p.name not in ('cpu_asm.o','ground_asm.o','objects_asm.o','packet_asm.o') and p.name not in replaced and not ((args.staged_conversion or args.deep_bw) and p.name=='monosh_boss_data.o'))
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
        key=fingerprint.hexdigest()+args.renderer+str(stride)+str(args.row_dirty)+str(args.row_dirty_bands)+str(args.row_dirty_step)+str(args.row_dirty_aligned)+str(args.bullet_cache)+str(args.row_dirty_exact)+str(args.bullet_opacity)
        suffix=('_256' if args.padded_pipeline else '')+('_rows' if args.row_dirty else '')+('_bands'+str(args.row_dirty_step) if args.row_dirty_bands else '')+('_aligned' if args.row_dirty_aligned else '')
        cache=BUILD/('compiled_cache'+suffix+'.bin');metadata=BUILD/('compiled_cache'+suffix+'.json')
        if cache.exists() and metadata.exists() and json.loads(metadata.read_text()).get('key')==key:
            rom=bytearray(cache.read_bytes())
            (BUILD/'compiled_game_packing.json').write_text(json.dumps(json.loads(metadata.read_text())['packing'],indent=2)+'\n')
        else:
            rom=compiled_cache(variants,BUILD,macros=args.renderer=='macros',stride=stride,row_dirty=args.row_dirty,row_dirty_bands=args.row_dirty_bands,row_dirty_step=args.row_dirty_step,row_dirty_aligned=args.row_dirty_aligned,bullet_cache=args.bullet_cache,row_dirty_exact=args.row_dirty_exact,bullet_opacity=args.bullet_opacity)
            cache.write_bytes(rom)
            metadata.write_text(json.dumps({'key':key,'packing':json.loads((BUILD/'compiled_game_packing.json').read_text())}))
    else:rom=build_cache(variants,BUILD,game=True)
    if args.left_hints:
        from sa1_left_hints import build as left_hints_build
        rom=left_hints_build(rom,BUILD)
        run([CC/'ca65.exe','-I',BUILD,'-o',BUILD/'left_hints.o',SA1/'left_hints_game.s'])
        run([CC/'ld65.exe','-C',BUILD/'game.cfg','-m',BUILD/'game.map','-Ln',BUILD/'game.lbl','-o',linked,*objs,CC.parent/'lib/none.lib'])
        new_labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
        assert new_labels==labels
        legacy=linked.read_bytes()
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
    if args.native_near:
        # C0の重複boot imageと、未使用になった背景展開表だけを再利用する。
        # DA..DDは地面palette、DFはplayer OBJなので保持する。
        oam=(BUILD/'native_near_oam.bin').read_bytes()
        rom[0x400000:0x410000]=oam[:0x10000]
        rom[0x5e0000:0x5f0000]=oam[0x10000:]
    if args.renderer=='macros':
        from sa1_background_compiled import build as compiled_background
        near=compiled_background(raw,BUILD)
        near_size=json.loads((BUILD/'compiled_background_packing.json').read_text())['payloadBytes']
        assert near_size<=0xb000
        assert args.row_dirty_aligned or json.loads((BUILD/'compiled_game_packing.json').read_text())['payloadEnd']<=0x7e0000
        rom[0x7e0000:0x7e0000+near_size]=near[:near_size]
    if args.compiled_ground:
        rom[0x10000:0x20000]=(BUILD/'ground_compiled.bin').read_bytes()
    if args.renderer=='macros':
        if args.compiled_ground:assert json.loads((BUILD/'ground_compiled_packing.json').read_text())['bytes']<=0xd400
        rom[0x1d400:0x1e400]=(BUILD/'flip_scales.bin').read_bytes()
    if args.dense_tiles or args.cpu_pack or args.direct_sparse:
        ppu=bytearray(rom[0x430000:0x440000])
        for i in range(32,768):struct.pack_into('<H',ppu,0xc000+i*2,0x2420)
        rom[0x430000:0x440000]=ppu
        (BUILD/'ppu_sa1.bin').write_bytes(ppu)
    if args.compact_memory:
        from sa1_compact_memory import finish as compact_finish
        compact_finish(rom,BUILD,labels,ppu)
    struct.pack_into('<H',rom,0x7ffc,labels['reset'])
    struct.pack_into('<H',rom,0x7fea,labels['nmi_game'])
    struct.pack_into('<H',rom,0x7ffa,labels['nmi_game'])
    if args.pipeline:
        struct.pack_into('<H',rom,0x7fee,labels['irq_game'])
        struct.pack_into('<H',rom,0x7ffe,labels['irq_game'])
    rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    path=BUILD/'MonoSHSA1_4bpp_game.sfc';path.write_bytes(rom)
    (BUILD/'manifest.json').write_text(json.dumps({'romSha256':hashlib.sha256(rom).hexdigest(),'sa1CodeBytes':labels['__SA1_SIZE__'],'renderer':args.renderer,'paddedFramebuffer':False,'directFramebuffer':args.renderer=='macros','tileDma':args.tile_dma,'bucketSort':args.bucket_sort,'pipeline':args.pipeline,'pipelineDirect':args.pipeline_direct,'pipelineIrq':args.pipeline_irq,'earlyRequest':args.early_request,'bitsetSort':args.bitset_sort,'listSort':args.list_sort,'smallEdgeJit':args.small_edge_jit,'compiledGround':args.compiled_ground,'unrollPpuDma':args.unroll_ppu_dma,'wideClear':args.wide_clear,'bulletCache':args.bullet_cache,'bulletWords':args.bullet_words,'denseTiles':args.dense_tiles,'bottomSlack':args.bottom_slack,'irqFastrom':args.irq_fastrom,'dirtyIram':args.dirty_iram,'cpuPack':args.cpu_pack,'leftHints':args.left_hints,'rightClipJit':args.right_clip_jit,'fallbackMask':args.fallback_mask,'fallbackEarly':args.fallback_early,'fallbackSa1':args.fallback_sa1,'pixelDelta':args.pixel_delta,'pixelDeltaMin':args.pixel_delta_min,'vramPrefetch3':args.vram_prefetch3,'vramPump':args.vram_pump,'deferStage':args.defer_stage,'lateFlip':args.late_flip,'sa1Game':args.sa1_game or args.sa1_game_compact,'sa1GameCompact':args.sa1_game_compact,'gameIrqWram':args.game_irq_wram,'gameWaitWai':args.game_wait_wai,'compactMemory':args.compact_memory,'splitMapDma':args.split_map_dma,'splitMapMvn':args.split_map_mvn,'gameStageOverlap':args.game_stage_overlap,'directSparse':args.direct_sparse,'prefixDma':args.prefix_dma,'prefixFastrom':args.prefix_fastrom,'mapDmaOverlap':args.map_dma_overlap,'prefixTable':args.prefix_table,'sparseMergeGap':args.sparse_merge_gap,'idleClear':args.idle_clear,'bulletLeftFast':args.bullet_left_fast,'bulletOpacity':args.bullet_opacity,'contiguousChrDma':args.contiguous_chr_dma,'prefixCpuTable':args.prefix_cpu_table,'wideClearMin':args.wide_clear_min,'pipelineDepth':args.pipeline_depth,'transferTiles':args.transfer_tiles,'redrawAll':args.redraw_all,'mergeDma':args.merge_dma,'clipEdges':args.clip_edges,'paddedPipeline':args.padded_pipeline,'workingFramebufferStride':256 if args.padded_pipeline else 128,'largeEdgeCache':args.large_edge_cache,'tripleBw':args.triple_bw,'deepBw':args.deep_bw,'framebufferSlots':5 if args.sa1_game else 7 if args.deep_bw else 3 if args.triple_bw else 2,'prefillCount':args.prefill_count,'fastDma':args.fast_dma,'cpuCodeCopy':args.cpu_code_copy,'cpuFill':args.cpu_fill,'cpuFar':args.cpu_far,'shapeCache':args.shape_cache,'temporalSort':args.temporal_sort,'stagedConversion':args.staged_conversion,'fastLeftClip':args.fast_left_clip,'skipFarClear':args.skip_far_clear,'linearShape':args.linear_shape,'cpuEdgeCopy':args.cpu_edge_copy,'prefillPipeline':args.prefill_pipeline,'packetShapes':args.packet_shapes,'offloadSort':args.offload_sort,'adaptiveVram':args.adaptive_vram,'radixSort':args.radix_sort,'keyBuckets':args.key_buckets,'nativeFar':args.native_far,'nativeBackground':args.native_background,'nativeNear':args.native_near,'frontDelta':args.front_delta,'rowDirty':args.row_dirty,'rowDirtyBands':args.row_dirty_bands,'waitSlots':args.wait_slots,'transferMask':args.transfer_mask,'occupancy':args.occupancy,'accurateDmaBudget':args.accurate_dma_budget,'frontMask':args.front_mask,'changedMask':args.changed_mask,'visibleMask':args.visible_mask,'rowDirtyStep':args.row_dirty_step,'rowDirtyAligned':args.row_dirty_aligned,'rowDirtyExact':args.row_dirty_exact,'stackFill':args.stack_fill,'stackBand':args.stack_band,'cpuCodeBank':0xc1 if args.fastrom_cpu else 0x7f,'stage':'prefetch-three-pages' if args.vram_prefetch3 else 'dirty-tiles-two-pages','goal60fpsAchieved':False},indent=2)+'\n')
    print(path)

if __name__=='__main__':main()
