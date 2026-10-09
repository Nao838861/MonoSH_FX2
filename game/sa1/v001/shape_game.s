; asset × 幅の表から高さを二分探索する。A=幅|高さ<<8、X=asset。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_find_shape: far
.segment "BOOT"
shapeLow=$f2
shapeHigh=$f4
shapeBase=$f6
shapeMid=$fa
shapeSize=$fc
sa1_find_shape:
  rep #$30
  sta shapeSize
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
  rtl
