; 近景の中央48/52pxをROMの8px断片で描く。末尾4pxも別の断片で厳密に描く。
.setcpu "65816"
.smart
.export sa1_near_row: far
.segment "BOOT"
nrSource=$a0
nrDest=$a2
nrRemain=$a4
nrTable=$a6
sa1_near_row:
  rep #$30
  phb
  lda $d0
  asl
  clc
  adc $010a
  and #511
  sta nrSource
  lda $e6
  clc
  adc $d0
  sta nrDest
  lda $d2
  sec
  sbc $d0
  sta nrRemain
  lda $e4
  xba
  asl
  asl
  sta nrTable
  sep #$20
  lda #$5c
  sta $07f0
  lda #$fe
  sta $07f3
  lda $0102
  pha
  plb
  rep #$20
nr_eight:
  lda nrRemain
  cmp #4
  bcc nr_four
  lda nrSource
  asl
  clc
  adc nrTable
  tax
  lda f:$fe0000,x
  sta f:$0007f1
  ldx nrDest
  jsl $0007f0
  lda nrDest
  clc
  adc #4
  sta nrDest
  lda nrSource
  clc
  adc #8
  and #511
  sta nrSource
  lda nrRemain
  sec
  sbc #4
  sta nrRemain
  bne nr_eight
  bra nr_done
nr_four:
  lda nrSource
  asl
  clc
  adc nrTable
  tax
  lda f:$fec400,x
  sta f:$0007f1
  ldx nrDest
  jsl $0007f0
nr_done:
  plb
  sep #$20
  lda #$22
  sta $07f0
  rep #$20
  rtl
