"""同じraw画像から、疎なCHRの転送先を直接VRAMへ並べる。"""
from sa1_dense import pipeline as dense_pipeline
from sa1_vram_prefetch import pipeline as vram_pipeline


def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def pipeline(text):
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
    return text
