; BWのraw画像を詰め直さず、転送先だけ連続CHRへ付け替える。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_sparse_direct_finish: far, sparse_direct_overflow: far
.segment "GSU"
.a16
.i16
sa1_sparse_direct_finish:
  rep #$30
  lda $011a
  asl
  sta $b0
  asl
  clc
  adc $b0
  sta $b0
  lda #2064
  sta $b2
  ldx #0
.ifdef SA1_PREFIX_TABLE
  stz $b4
  stz $b6
  lda $019a
  clc
  adc #$6600
  sta $b8
  lda $0102
  sta $ba
  ldy #0
.endif
direct_descriptor:
  cpx $b0
  bcs direct_map
  lda $b2
  sta f:$430804,x
  lda f:$430800,x
  lsr
  clc
  adc $b2
  cmp #8193
  jcs sparse_direct_overflow
  sta $b2
.ifdef SA1_PREFIX_TABLE
  lda f:$430800,x
  sta $bc
  clc
  adc $b4
  sta $b4
  sta [$b8],y
  iny
  iny
  lda $bc
  .repeat 5
    lsr
  .endrepeat
  sta $be
  lsr
  lsr
  clc
  adc $be
  adc $bc
  adc #64
  adc $b6
  sta $b6
  sta [$b8],y
  iny
  iny
.endif
  txa
  clc
  adc #6
  tax
  bra direct_descriptor
direct_map:
  lda #1472
  sta f:$430800,x
  lda #$6040
  sta f:$430802,x
  lda #$0420
  sta f:$430804,x
  inc $011a
  lda $0118
  clc
  adc #1472
  sta $0118
  rtl
sparse_direct_overflow:
  stp
