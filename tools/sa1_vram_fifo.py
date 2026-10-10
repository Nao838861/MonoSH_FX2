"""固定素材を維持し、SA-1で可変長CHR FIFOと配置表を作る。"""
from sa1_vram_four import change


def check_map_bw_layout(rom,labels):
    """描画余白・累積表・12配置表が独立することをリンク後の表で確認する。"""
    import struct
    from sa1_deep_buffers import SLOTS
    address=labels['fifo_bw_map_bases']
    assert address>>16==1
    start=0x8000+(address&0x7fff)
    words=struct.unpack_from('<24H',rom,start)
    maps=list(zip(words[1::2],words[::2]))
    assert len(set(maps))==12
    for i,(bank,begin) in enumerate(maps):
        end=begin+1472
        assert end<=65536
        for slot in SLOTS:
            raw_bank=slot&255;raw_base=slot&0x8400
            if bank==raw_bank:
                assert end<=raw_base-1024 or begin>=raw_base+208*128
                assert end<=raw_base+0x6600 or begin>=raw_base+0x6600+50*4
        for other_bank,other_begin in maps[:i]:
            assert bank!=other_bank or end<=other_begin or begin>=other_begin+1472


def sparse_map(text,fast=False,fused=False,cpu=False,fast_fill=False,map_bw=False):
    if fast:text=text.replace('$430800','$434000').replace('$430804','$434004')
    text=text.replace('$2420','$2400').replace('$2421','$2401')
    text='.setcpu "65816"\n.import sa1_fifo_allocate: far\n'+text
    text=change(text,'sa1_sparse_map_prepare:\n  rep #$30\n',
                'sa1_sparse_map_prepare:\n  rep #$30\n  jsl sa1_fifo_allocate\n')
    if map_bw:
        text=change(text,'  lda $019a\n  clc\n  adc #$6040\n','  lda $01a8\n')
        text=change(text,'  lda $0102\n  and #255\n','  lda $01aa\n  and #255\n')
    if cpu:
        begin=text.index('sa1_sparse_map_prepare:\n')
        end=text.index('sm_empty_map:\n',begin)
        return text[:begin]+'sa1_sparse_map_prepare:\n  jsl sa1_fifo_allocate\n  rtl\n'+text[end:]
    if fast_fill:
        begin=text.index('sm_fill_cpu:\n');end=text.index('sm_map_ready:\n',begin)
        text=text[:begin]+'''sm_fill_cpu:
  phb
  sep #$20
  lda smBank
  pha
  plb
  rep #$30
  ldx smMap
  ldy #23
  lda #$2400
sm_fill_fast:
  .repeat 32,I
    sta a:I*2,x
  .endrepeat
  txa
  clc
  adc #64
  tax
  lda #$2400
  dey
  bne sm_fill_fast
  plb
'''+text[end:]
    text=change(text,'  lda #$2401\n  sta smTile',
                '  lda $01a0\n  sec\n  sbc $01a2\n  ora #$2400\n  sta smTile')
    if fused:
        begin=text.index('sm_map_ready:\n')
        end=text.index('sm_empty_map:\n',begin)
        return text[:begin]+'sm_map_ready:\n  rtl\n'+text[end:]
    return change(text,'  inc\n  iny\n  iny\n  dec smCount', '''  inc
  cmp $ce
  bne :+
  clc
  adc #544
:
  bit #255
  bne :+
  inc
:
  iny
  iny
  dec smCount''')


def pipeline(text,build,depth,archive=False,cpu=False,map_bw=False):
    if archive or map_bw:
        begin=text.index('  .ifdef SA1_DEEP_BW\n',text.index('  jsl four_map_flip\n'))
        end=text.index('  ldx pipe_record_offset\n',begin)
        release=text[begin:end]
        assert 'stz pipe_bw_busy,x' in release
        text=text[:begin]+text[end:]
        text=change(text,'  jsr p3Complete\n',release+'  jsr p3Complete\n')
    text=change(text,'p3Queue: .res 6','p3Queue: .res '+str(depth*2))
    text=change(text,'  lda p3Count\n  cmp #3\n','  lda p3Count\n  cmp #'+str(depth-1)+'\n')
    text=change(text,'  inc pipe_initialized\n','  inc pipe_initialized\n  lda #0\n  sta f:$437e02\n')
    text=change(text,'  lda p3NextPage\n  .ifndef SA1_FRONT_MASK',
                '  lda pipe_records+6,x\n  .ifndef SA1_FRONT_MASK')
    old='  cmp #2\n  jne pipe_irq_done\n'
    assert text.count(old)==1
    text=change(text,old,old+'''  txa
  .repeat 8
    asl
  .endrepeat
  tax
  lda pipe_records+36,x
  sec
  sbc f:$437e02
  cmp #1506
  jcs pipe_irq_done
  lda pipe_read_slot
  asl
  tax
''')
    text=change(text,'  stz pipe_status,x\n:\n  lda pipe_target_slot', '''  stz pipe_status,x
  txa
  .repeat 8
    asl
  .endrepeat
  tax
  lda pipe_records+38,x
  clc
  adc f:$437e02
  sta f:$437e02
:
  lda pipe_target_slot''')
    text=change(text,'  ora #$40\n','  ora #$50\n')
    if map_bw:
        text='.import fifo_bw_map_bases: far\n'+text
        text=change(text,'  sta pipe_main_offset\n  tax\n', '''  sta pipe_main_offset
  phx
  .repeat 7
    lsr
  .endrepeat
  tax
  lda f:fifo_bw_map_bases,x
  sta f:$0031a8
  lda f:fifo_bw_map_bases+2,x
  sta f:$0031aa
  plx
  lda pipe_main_offset
  tax
''')
    ring=(build/'vram_four_cpu.inc').read_text(encoding='utf-8')
    assert ring.count('  cmp #3\n')==2
    ring=ring.replace('  cmp #3\n','  cmp #'+str(depth)+'\n')
    begin=ring.index('  lda p3NextPage\n');end=ring.index('  sta p3NextPage\n',begin)+len('  sta p3NextPage\n')
    ring=ring[:begin]+ring[end:]
    if cpu:
        text='.import fifo_map_deferred: far\n'+text
        text=change(text,'render_started:\n  lda #1\n  sta f:$003100\n',
                    'render_started:\n  lda #1\n  sta f:$003100\n  php\n  cli\n  jsl $7f0000+fifo_map_deferred\n  plp\n')
        split=ring.index('p3Flip:\n')
        ring=ring[:split]+change(ring[split:],'  lda pipe_target_slot\n  pha\n', '''  lda p3Head
  asl
  tax
  lda p3Queue,x
  .repeat 9
    asl
  .endrepeat
  tax
  lda pipe_records+62,x
  cmp #1
  beq :+
  rts
:
  lda pipe_target_slot
  pha
''')
    (build/'vram_fifo_cpu.inc').write_text(ring,encoding='utf-8')
    return change(text,'.include "vram_four_cpu.inc"','.include "vram_fifo_cpu.inc"')
