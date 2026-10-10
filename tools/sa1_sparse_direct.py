"""同じraw画像から、疎なCHRの転送先を直接VRAMへ並べる。"""
from sa1_dense import pipeline as dense_pipeline
from sa1_vram_prefetch import pipeline as vram_pipeline


def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def pipeline(text,prefix=False,prefix_fastrom=False,map_overlap=False,contiguous=False):
    text=vram_pipeline(dense_pipeline(text))
    text=replace(text,'  lda #$01\n  sta f:$002231','  lda #$15\n  sta f:$002231')
    # 最後の記述子だけが生のmap。それ以前は256px幅のCC type1。
    old='  lda pipe_records+4,x\n  beq :+\n  sep #$20\n  lda #$81\n  sta f:$002231\n:\n'
    new='  lda pipe_records+4,x\n  clc\n  adc #6\n  cmp pipe_records+2,x\n  bne :+\n  sep #$20\n  lda #$95\n  sta f:$002231\n:\n'
    text=replace(text,old,new)
    old='  sta pipe_records+4,x\n  sep #$20\n  lda #$81\n  sta f:$002231\n  rep #$20\n  jmp pipe_descriptor'
    new='  sta pipe_records+4,x\n  clc\n  adc #6\n  cmp pipe_records+2,x\n  bne :+\n  sep #$20\n  lda #$95\n  sta f:$002231\n  rep #$20\n:\n  jmp pipe_descriptor'
    text=replace(text,old,new)
    old='  lda #$81\n  sta f:$002231\n  rep #$20\n  txa\n  clc\n  adc #6\n  tax\n  cpx pipe_fast_end\n  bcc pipe_fast_loop'
    new='  rep #$20\n  txa\n  clc\n  adc #6\n  tax\n  clc\n  adc #6\n  cmp pipe_fast_end\n  bne :+\n  sep #$20\n  lda #$95\n  sta f:$002231\n  rep #$20\n:\n  cpx pipe_fast_end\n  bcc pipe_fast_loop'
    text=replace(text,old,new)
    # 展開DMAはCHRの記述子だけを送り、最後の生mapを別に送る。
    old='  sbc pipe_records+4,x\n  sta pipe_fast_end\n'
    text=replace(text,old,'  sbc pipe_records+4,x\n  sec\n  sbc #6\n  sta pipe_fast_end\n')
    text=text.replace('.repeat 49, I','.repeat 50, I')
    text=text.replace('lda f:$7f0000+pipe_fast_entries','lda f:pipe_fast_entries')
    text=text.replace('pipe_fast_entries:\n','  .segment "GSU"\npipe_fast_entries:\n')
    text=text.replace('pipe_fast_groups_done:\n','  .segment "CODE"\npipe_fast_groups_done:\n')
    text=replace(text,'pipe_fast_groups_done:\n  .else','''pipe_fast_groups_done:
  sep #$20
  lda #$95
  sta f:$002231
  rep #$20
  ldx pipe_desc_offset
  lda pipe_records,x
  sta f:$004305
  lda pipe_records+2,x
  sta f:$004302
  lda pipe_records+4,x
  clc
  adc pipe_fast_page
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  .else''')
    if prefix:text=prefix_pipeline(text,fastrom=prefix_fastrom)
    if map_overlap:text=overlap_pipeline(text)
    if contiguous:text=contiguous_pipeline(text)
    return text


def contiguous_pipeline(text):
    # CHRの転送先は全記述子で連続する。まとまりの先頭だけVMADDRを設定する。
    start=text.index('pipe_fast_unroll_start:\n');end=text.index('pipe_fast_unroll_end:\n',start)
    block=text[start:end]
    old='''  lda pipe_records-68+I*6,x
  ; 全destinationは$8000未満。各ADC後もcarry=0を維持する。
  adc pipe_fast_page
  sta f:$002116
'''
    assert block.count(old)==1
    text=text[:start]+block.replace(old,'',1)+text[end:]
    text=replace(text,'pipe_fast_begin:\n  nop\n','''pipe_fast_begin:
  ldx pipe_desc_offset
  lda pipe_records+4,x
  clc
  adc pipe_fast_page
  sta f:$002116
''')
    text=text.replace('=12*34','=12*24').replace('.min(I,12)*34','.min(I,12)*24')
    old='''  lda pipe_dma_chunk
  asl
  asl
  clc
  adc pipe_dma_chunk
  asl
  clc
  adc pipe_cost_bytes'''
    new='''  lda pipe_dma_chunk
  asl
  asl
  asl
  clc
  adc pipe_cost_bytes'''
    return replace(text,old,new)


def overlap_pipeline(text):
    # CCを使わないmap転送中はSA-1自身のDMAを解放する。
    # 次のraw画像へ移るとき、CC設定の前に使用権を取り直す。
    begin=text.index('pipe_setup_transfer:\n')
    marker='  .ifndef SA1_STAGED\n  sep #$20\n  lda #$15\n'
    position=text.index(marker,begin)
    acquire='''  lda f:$00311e
  bne sd_engine_owned
  lda #0
  sta f:$00311c
  lda #1
  sta f:$00311e
  sep #$20
  lda #$80
  sta f:$002200
  rep #$20
sd_engine_wait:
  lda f:$00311c
  cmp #2
  bne sd_engine_wait
sd_engine_owned:
'''
    text=text[:position]+acquire+text[position:]
    # 8bit Aで311eの下位だけを解放する。上位は常に0。
    text=text.replace('  lda #$95\n  sta f:$002231','  lda #$95\n  sta f:$002231\n  lda #0\n  sta f:$00311e')
    return text


def prefix_pipeline(text,fastrom=False):
    text='.import pipe_prefix_plan: far, pfPartial, pfBytes, pfDesc\n.export pipe_time_left, pipe_fast_partial_done\n'+text
    # 展開ブロックを01:xxxxへ移し、CODEの空きを確保する。
    # SA-1の81は01のミラーではない。2222の再設定はE0..EFの素材を壊す。
    text=replace(text,'pipe_fast_unroll_start:\n','  .segment "GSU"\npipe_fast_unroll_start:\n')
    text=replace(text,'pipe_fast_unroll_end:\n  rts','pipe_fast_unroll_end:\n  rtl')
    text=text.replace('.word pipe_fast_unroll_end-.min(I,24)*34','.word .loword(pipe_fast_unroll_end-.min(I,24)*34)')
    text=replace(text,'  jsr pipe_fast_gate\n','  jsl $c10000+pipe_fast_gate\n')
    text=replace(text,'  lda #$c1\n  sta pipe_irq_gate+2','  lda #$01\n  sta pipe_irq_gate+2')
    old='  lda pipe_dma_chunk\n  asl\n  asl\n  clc\n  adc pipe_dma_chunk\n  asl\n  clc\n  adc pipe_cost_bytes'
    new='  lda pipe_dma_chunk\n  asl\n  clc\n  adc pipe_dma_chunk\n  asl\n  asl\n  clc\n  adc pipe_cost_bytes'
    text=replace(text,old,new)
    old='  jcs pipe_fast_unavailable\n  lda pipe_records+34,x\n  clc\n  adc fx4_dma_bytes'
    new='''  bcc pf_full_frame
  jsl $c10000+pipe_prefix_plan
  jcc pipe_fast_unavailable
  ldx pipe_record_offset
  lda pfBytes
  bra pf_frame_bytes
pf_full_frame:
  stz pfPartial
  lda pipe_records+34,x
pf_frame_bytes:
  clc
  adc fx4_dma_bytes'''
    text=replace(text,old,new)
    old='  lda pipe_records+2,x\n  clc\n  adc pipe_record_offset\n  adc #208\n  sta pipe_fast_end'
    new='''  lda pfPartial
  beq pf_full_end
  lda pipe_records+4,x
  clc
  adc pfDesc
  bra pf_end_ready
pf_full_end:
  lda pipe_records+2,x
pf_end_ready:
  clc
  adc pipe_record_offset
  adc #208
  sta pipe_fast_end'''
    text=replace(text,old,new)
    old='  lda pipe_records+2,x\n  sec\n  sbc pipe_records+4,x\n  sec\n  sbc #6\n  sta pipe_fast_end'
    new='''  lda pfPartial
  beq pf_unroll_full
  lda pfDesc
  bra pf_unroll_ready
pf_unroll_full:
  lda pipe_records+2,x
  sec
  sbc pipe_records+4,x
  sec
  sbc #6
pf_unroll_ready:
  sta pipe_fast_end'''
    text=replace(text,old,new)
    text=replace(text,'pipe_fast_groups_done:\n  sep #$20','pipe_fast_groups_done:\n  lda pfPartial\n  jne pipe_fast_partial_done\n  sep #$20')
    text+='''
.segment "CODE"
pipe_fast_partial_done:
  ldx pipe_record_offset
  lda pipe_records+4,x
  clc
  adc pfDesc
  sta pipe_records+4,x
  clc
  adc #6
  cmp pipe_records+2,x
  bne pf_partial_chr_remain
  sep #$20
  lda #$95
  sta f:$002231
  rep #$20
pf_partial_chr_remain:
  lda pipe_records+34,x
  sec
  sbc pfBytes
  sta pipe_records+34,x
  clc
  rts
'''
    if fastrom:
        text=replace(text,'  .segment "GSU"\npipe_fast_unroll_start:','pipe_fast_unroll_start:')
        text=replace(text,'  lda #$01\n  sta pipe_irq_gate+2','  lda #$c1\n  sta pipe_irq_gate+2')
        text=replace(text,'  cmp #145\n  bcc :+\n  lda #144','  cmp #73\n  bcc :+\n  lda #72')
        start=text.index('pipe_fast_unroll_start:\n');end=text.index('  .segment "CODE"\npipe_fast_groups_done:',start)
        block=text[start:end].replace('.repeat 24, I','.repeat 12, I').replace('pipe_records-144','pipe_records-72').replace('pipe_records-142','pipe_records-70').replace('pipe_records-140','pipe_records-68').replace('=24*34','=12*34').replace('.min(I,24)','.min(I,12)')
        text=text[:start]+block+text[end:]
        old='  lda pipe_dma_chunk\n  asl\n  clc\n  adc pipe_dma_chunk\n  asl\n  asl\n  clc\n  adc pipe_cost_bytes'
        new='  lda pipe_dma_chunk\n  asl\n  asl\n  clc\n  adc pipe_dma_chunk\n  asl\n  clc\n  adc pipe_cost_bytes'
        text=replace(text,old,new)
    return text
