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
dirty_rows_run:
  ldy #0
  lda [rowPtr],y
  and #255
  sta rowRun
  iny
  lda [rowPtr],y
  and #255
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
  iny
  lda [rowPtr],y
  and #255
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
  adc #3
  sta rowPtr
  lda rowRemain
  sec
  sbc rowRun
  sta rowRemain
  jne dirty_rows_run
  rtl
