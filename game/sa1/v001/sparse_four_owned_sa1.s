; 319tileの後でmap領域を飛ばし、末尾の未表示map行に16tileを置く。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_sparse_direct_finish: far, sparse_direct_overflow: far
.ifndef SA1_PREFIX_DESC_COST
SA1_PREFIX_DESC_COST=64
.endif
.segment "GSU"
oInput=$a0
oEnd=$a2
oOutput=$a4
oDest=$a6
oLength=$a8
oSource=$aa
oBefore=$ac
.a16
.i16
sa1_sparse_direct_finish:
  rep #$30
  lda $011a
  asl
  sta oEnd
  asl
  clc
  adc oEnd
  sta oEnd
  stz oInput
  stz oOutput
  lda #16
  sta oDest
owned_descriptor:
  ldx oInput
  cpx oEnd
  jcs owned_map
  lda f:$430800,x
  sta oLength
  lda f:$430802,x
  sta oSource
  lda oDest
  cmp #$1400
  bne :+
  lda #$1700
  sta oDest
:
  cmp #$1700
  bcs owned_whole
  lda #$1400
  sec
  sbc oDest
  asl
  cmp oLength
  bcs owned_whole
  sta oBefore
  lda oLength
  pha
  lda oBefore
  sta oLength
  jsr owned_emit
  pla
  sec
  sbc oBefore
  sta oLength
  lda oSource
  clc
  adc oBefore
  sta oSource
  lda #$1700
  sta oDest
owned_whole:
  jsr owned_emit
  lda oInput
  clc
  adc #6
  sta oInput
  bra owned_descriptor
owned_emit:
  lda oLength
  jeq sparse_direct_overflow
  ldy oOutput
  cpy #294
  jcs sparse_direct_overflow
  tyx
  sta f:$434000,x
  lda oSource
  sta f:$434002,x
  lda oDest
  sta f:$434004,x
  lda oLength
  lsr
  clc
  adc oDest
  cmp #$1801
  jcs sparse_direct_overflow
  sta oDest
  tya
  clc
  adc #6
  sta oOutput
  rts
owned_map:
  ldx oOutput
  lda #1472
  sta f:$434000,x
  lda #$6040
  sta f:$434002,x
  lda #$1420
  sta f:$434004,x
  txa
  clc
  adc #6
  sta oEnd
  ldx #0
owned_copy:
  lda f:$434000,x
  sta f:$430800,x
  inx
  inx
  cpx oEnd
  bcc owned_copy
  lda $011a
  clc
  adc #1
  sta $011a
  lda oEnd
  cmp oInput
  sec
  sbc oInput
  cmp #12
  bne :+
  inc $011a
:
  lda $0118
  clc
  adc #1472
  sta $0118
.ifdef SA1_PREFIX_TABLE
  stz $b4
  stz $b6
  lda $019a
  clc
  adc #$6600
  sta $b8
  lda $0102
  sta $ba
  ldx #0
  ldy #0
owned_costs:
  cpx oOutput
  bcs owned_costs_done
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
  adc #SA1_PREFIX_DESC_COST
  adc $b6
  sta $b6
  sta [$b8],y
  iny
  iny
  txa
  clc
  adc #6
  tax
  bra owned_costs
owned_costs_done:
.endif
  rtl
sparse_direct_overflow:
  stp
