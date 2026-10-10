; 行ごとの不透明範囲を4px単位のRLEで持ち、必要なtile bandだけ更新する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dirty_row_rect: far
.ifdef SA1_ROW_DIRTY_ALIGNED
.import sa1_tile_masks
.endif
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
  .ifdef SA1_ROW_DIRTY_EXACT
  ldy #2
  lda [rowPtr],y
  and #255
  .else
  .repeat 13
    lsr
  .endrepeat
  inc
  .endif
  sta $d6
  asl
  asl
  asl
  sta rowRun
  lda $d4
  .ifdef SA1_ROW_DIRTY_EXACT
  and #255
  .else
  and #63
  .endif
  .else
  and #255
  sta rowRun
  iny
  lda [rowPtr],y
  and #255
  .endif
  .ifndef SA1_ROW_DIRTY_EXACT
  asl
  asl
  .endif
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
  .ifdef SA1_ROW_DIRTY_EXACT
  xba
  and #255
  .else
  .repeat 6
    lsr
  .endrepeat
  and #127
  .endif
  .else
  iny
  lda [rowPtr],y
  and #255
  .endif
  jeq dirty_rows_next
  .ifndef SA1_ROW_DIRTY_EXACT
  asl
  asl
  .endif
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
  .ifdef SA1_ROW_DIRTY_ALIGNED
  jsr dirty_aligned_rect
  .else
  jsl sa1_dirty_row_rect
  .endif
dirty_rows_next:
  lda rowTop
  clc
  adc rowRun
  sta rowTop
  lda rowPtr
  clc
  .ifdef SA1_ROW_DIRTY_ALIGNED
  .ifdef SA1_ROW_DIRTY_EXACT
  adc #3
  .else
  adc #2
  .endif
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

.ifdef SA1_ROW_DIRTY_ALIGNED
; この経路は上下端が既に8px単位。汎用矩形の再丸めを省く。
dirty_aligned_rect:
  lda drTop
  bpl :+
  lda #0
:
  cmp #192
  bcs dirty_aligned_done
  lsr
  pha
  lda drBottom
  bmi dirty_aligned_pop
  cmp #193
  bcc :+
  lda #192
:
  lsr
  sta drBottom
  lda drRight
  tax
  lda sa1_tile_masks,x
  sta $bc
  lda sa1_tile_masks+2,x
  sta $be
  lda drLeft
  tax
  lda sa1_tile_masks,x
  eor $bc
  sta $bc
  lda sa1_tile_masks+2,x
  eor $be
  sta $be
  plx
  cpx drBottom
  bcs dirty_aligned_done
dirty_aligned_band:
  .ifdef SA1_DEEP_BW
  lda f:$432800,x
  ora $bc
  sta f:$432800,x
  lda f:$432802,x
  ora $be
  sta f:$432802,x
  .else
  lda f:$436800,x
  ora $bc
  sta f:$436800,x
  lda f:$436802,x
  ora $be
  sta f:$436802,x
  .endif
  lda drLeft
  cmp $0120,x
  bcs :+
  sta $0120,x
:
  lda drRight
  cmp $0122,x
  bcc :+
  sta $0122,x
:
  inx
  inx
  inx
  inx
  cpx drBottom
  bcc dirty_aligned_band
dirty_aligned_done:
  rts
dirty_aligned_pop:
  pla
  rts
.endif
