; 行ごとの不透明範囲を4px単位のRLEで持ち、必要なtile bandだけ更新する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dirty_row_rect: far
.export sa1_dirty_rows: far
.segment "BOOT"
drLeft=$a8
drRight=$aa
drTop=$ac
drBottom=$ae
drHeight=$b2
rowPtr=$c8
rowLeft=$cc
rowTop=$ce
rowRemain=$d0
rowRun=$d2
sa1_dirty_rows:
  rep #$30
  lda f:$ff0007,x
  sta rowPtr
  sep #$20
  lda f:$ff0009,x
  sta rowPtr+2
  rep #$20
  lda drLeft
  sta rowLeft
  lda drTop
  sta rowTop
  lda drHeight
  sta rowRemain
  .ifdef SA1_ROW_DIRTY_ALIGNED
  lda rowTop
  and #7
  sta $d6
  asl
  clc
  adc $d6
  tay
  lda [rowPtr],y
  sta $d4
  iny
  iny
  sep #$20
  lda [rowPtr],y
  sta rowPtr+2
  rep #$20
  lda $d4
  sta rowPtr
  lda rowTop
  and #$fff8
  sta rowTop
  lda rowRemain
  clc
  adc $d6
  adc #7
  lsr
  lsr
  lsr
  sta rowRemain
  .endif
dirty_rows_run:
  ldy #0
  lda [rowPtr],y
  .ifdef SA1_ROW_DIRTY_ALIGNED
  sta $d4
  .repeat 13
    lsr
  .endrepeat
  inc
  sta $d6
  asl
  asl
  asl
  sta rowRun
  lda $d4
  and #63
  .else
  and #255
  sta rowRun
  iny
  lda [rowPtr],y
  and #255
  .endif
  asl
  asl
  clc
  adc rowLeft
  bpl :+
  lda #0
:
  cmp #256
  jcs dirty_rows_next
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  sta drLeft
  .ifdef SA1_ROW_DIRTY_ALIGNED
  lda $d4
  .repeat 6
    lsr
  .endrepeat
  and #127
  .else
  iny
  lda [rowPtr],y
  and #255
  .endif
  jeq dirty_rows_next
  asl
  asl
  clc
  adc rowLeft
  jmi dirty_rows_next
  cmp #257
  bcc :+
  lda #256
:
  clc
  adc #7
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  sta drRight
  lda rowTop
  sta drTop
  clc
  adc rowRun
  sta drBottom
  jsl sa1_dirty_row_rect
dirty_rows_next:
  lda rowTop
  clc
  adc rowRun
  sta rowTop
  lda rowPtr
  clc
  .ifdef SA1_ROW_DIRTY_ALIGNED
  adc #2
  .else
  adc #3
  .endif
  sta rowPtr
  lda rowRemain
  sec
  .ifdef SA1_ROW_DIRTY_ALIGNED
  sbc $d6
  .else
  sbc rowRun
  .endif
  sta rowRemain
  jne dirty_rows_run
  rtl
