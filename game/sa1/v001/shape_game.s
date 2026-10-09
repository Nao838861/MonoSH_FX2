; asset × 幅の表から高さを二分探索する。A=幅|高さ<<8、X=asset。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_find_shape: far
.ifdef SA1_SHAPE_CACHE
.export sa1_shape_cache_init: far
.endif
.segment "BOOT"
shapeLow=$f2
shapeHigh=$f4
shapeBase=$f6
shapeMid=$fa
shapeSize=$fc
sa1_find_shape:
  rep #$30
  sta shapeSize
.ifdef SA1_SHAPE_CACHE
  stx shapeHigh
  txa
  asl
  asl
  asl
  eor shapeSize
  and #255
  asl
  asl
  asl
  tax
  stx $fe
  lda f:$434000,x
  cmp shapeSize
  bne shape_cache_miss
  lda f:$434002,x
  cmp shapeHigh
  bne shape_cache_miss
  lda f:$434004,x
  tax
  rtl
shape_cache_miss:
  lda shapeSize
  sta f:$434000,x
  lda shapeHigh
  sta f:$434002,x
  tax
.endif
  txa
  xba
  asl
  sta shapeBase
  lda shapeSize
  and #255
  asl
  clc
  adc shapeBase
  tax
  lda f:$ff0000,x
  tax
  .ifdef SA1_LINEAR_SHAPE
  inx
shape_linear_search:
  sep #$20
  lda f:$ff0000,x
  cmp shapeSize+1
  beq shape_found
  rep #$20
  txa
  clc
  adc #7
  tax
  bra shape_linear_search
  .endif
  inc
  sta shapeBase
  lda f:$ff0000,x
  and #255
  sta shapeHigh
  stz shapeLow
shape_search:
  lda shapeLow
  clc
  adc shapeHigh
  lsr
  sta shapeMid
  asl
  asl
  asl
  sec
  sbc shapeMid
  clc
  adc shapeBase
  tax
  sep #$20
  lda f:$ff0000,x
  cmp shapeSize+1
  beq shape_found
  rep #$20
  bcc shape_higher
  lda shapeMid
  sta shapeHigh
  bra shape_search
shape_higher:
  lda shapeMid
  inc
  sta shapeLow
  bra shape_search
shape_found:
  rep #$20
.ifdef SA1_SHAPE_CACHE
  txa
  ldx $fe
  sta f:$434004,x
  tax
.endif
  rtl

.ifdef SA1_SHAPE_CACHE
sa1_shape_cache_init:
  rep #$30
  lda #$0800
  sta $2238
  lda #$8000
  sta $2232
  lda #$4000
  sta $2235
  sep #$20
  lda #2
  sta $2234
  lda #$84
  sta $2230
  lda #$43
  sta $2237
  rep #$30
  rtl
.endif
