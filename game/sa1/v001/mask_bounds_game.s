; 完成した32tile集合の最初/最後から、元と同じraw消去範囲を一度だけ求める。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_byte_extents: far
.export sa1_mask_bounds: far, sa1_mask_bounds_done: far
.segment "GSU"
mbLow=$e0
mbHigh=$e2
mbIndex=$e4
mbOffset=$e6
sa1_mask_bounds:
  rep #$30
  ldx #0
mb_band:
  lda f:$432800,x
  sta mbLow
  lda f:$432802,x
  sta mbHigh
  ora mbLow
  jeq mb_empty
  stx mbIndex
  lda mbLow
  and #255
  bne mb_left_zero
  lda mbLow
  xba
  and #255
  bne mb_left_eight
  lda mbHigh
  and #255
  bne mb_left_sixteen
  lda #96
  sta mbOffset
  lda mbHigh
  xba
  and #255
  bra mb_left_lookup
mb_left_zero:
  stz mbOffset
  bra mb_left_lookup
mb_left_eight:
  pha
  lda #32
  sta mbOffset
  pla
  bra mb_left_lookup
mb_left_sixteen:
  pha
  lda #64
  sta mbOffset
  pla
mb_left_lookup:
  asl
  tax
  lda f:sa1_byte_extents,x
  and #255
  clc
  adc mbOffset
  ldx mbIndex
  sta $0120,x
  lda mbHigh
  xba
  and #255
  bne mb_right_twentyfour
  lda mbHigh
  and #255
  bne mb_right_sixteen
  lda mbLow
  xba
  and #255
  bne mb_right_eight
  stz mbOffset
  lda mbLow
  and #255
  bra mb_right_lookup
mb_right_twentyfour:
  pha
  lda #96
  sta mbOffset
  pla
  bra mb_right_lookup
mb_right_sixteen:
  pha
  lda #64
  sta mbOffset
  pla
  bra mb_right_lookup
mb_right_eight:
  pha
  lda #32
  sta mbOffset
  pla
mb_right_lookup:
  asl
  tax
  lda f:sa1_byte_extents,x
  xba
  and #255
  clc
  adc mbOffset
  ldx mbIndex
  sta $0122,x
  bra mb_next
mb_empty:
  lda #128
  sta $0120,x
  stz $0122,x
mb_next:
  inx
  inx
  inx
  inx
  cpx #96
  jcc mb_band
sa1_mask_bounds_done:
  rtl
