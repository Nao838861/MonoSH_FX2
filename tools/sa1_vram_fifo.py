"""固定素材を維持し、SA-1で可変長CHR FIFOと配置表を作る。"""
from sa1_vram_four import change


def sparse_map(text,fast=False,fused=False):
    if fast:text=text.replace('$430800','$434000').replace('$430804','$434004')
    text=text.replace('$2420','$2400').replace('$2421','$2401')
    text='.setcpu "65816"\n.import sa1_fifo_allocate: far\n'+text
    text=change(text,'sa1_sparse_map_prepare:\n  rep #$30\n',
                'sa1_sparse_map_prepare:\n  rep #$30\n  jsl sa1_fifo_allocate\n')
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


def pipeline(text,build,depth,archive=False):
    if archive:
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
    ring=(build/'vram_four_cpu.inc').read_text(encoding='utf-8')
    assert ring.count('  cmp #3\n')==2
    ring=ring.replace('  cmp #3\n','  cmp #'+str(depth)+'\n')
    begin=ring.index('  lda p3NextPage\n');end=ring.index('  sta p3NextPage\n',begin)+len('  sta p3NextPage\n')
    ring=ring[:begin]+ring[end:]
    (build/'vram_fifo_cpu.inc').write_text(ring,encoding='utf-8')
    return change(text,'.include "vram_four_cpu.inc"','.include "vram_fifo_cpu.inc"')
