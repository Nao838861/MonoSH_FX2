; 4個のbyte位置を表に畳み込み、加算/退避とzero wordの反復探索を省く。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_byte_extents: far
.export sa1_mask_bounds: far, sa1_mask_bounds_done: far
.segment "GSU"
mbLow=$e0
mbHigh=$e2
sa1_mask_bounds:
  rep #$30
  ldx #0
mb_band:
  txy
  lda f:$432800,x
  sta mbLow
  lda f:$432802,x
  sta mbHigh
  ora mbLow
  jeq mb_empty
  lda mbLow
  bne mb_left_low_word
  lda mbHigh
  and #255
  bne mb_left_sixteen
  lda mbHigh
  xba
  and #255
  ora #768
  bra mb_left_lookup
mb_left_sixteen:
  ora #512
  bra mb_left_lookup
mb_left_low_word:
  and #255
  bne mb_left_lookup
  lda mbLow
  xba
  and #255
  ora #256
mb_left_lookup:
  asl
  tax
  lda f:sa1_byte_extents,x
  and #255
  tyx
  sta $0120,x
  lda mbHigh
  bne mb_right_high_word
  lda mbLow
  xba
  and #255
  bne mb_right_eight
  lda mbLow
  and #255
  bra mb_right_lookup
mb_right_eight:
  ora #256
  bra mb_right_lookup
mb_right_high_word:
  xba
  and #255
  bne mb_right_twentyfour
  lda mbHigh
  and #255
  ora #512
  bra mb_right_lookup
mb_right_twentyfour:
  ora #768
mb_right_lookup:
  asl
  tax
  lda f:sa1_byte_extents,x
  xba
  and #255
  tyx
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
