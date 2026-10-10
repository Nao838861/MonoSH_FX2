; 反転する敵弾を元のQ8.8 samplingで描く。通常向きはコンパイルドを維持する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_flip_bullet: far
.segment "GSU"
fuStep=$60
fvStep=$62
fuStart=$64
fv=$66
fu=$68
fAsset=$6a
fSource=$6c
fDest=$70
fRow=$74
fDy=$76
fDx=$78
fPixel=$7a
fData=$80
fSourceRow=$82
fScreenX=$84

sa1_flip_bullet:
  rep #$30
  lda $3e
  sec
  sbc #6
  cmp #3
  bcc flip_asset_ready
  lda #3
flip_asset_ready:
  sta fAsset
  xba
  asl
  asl
  sta fData
  lda $34
  asl
  clc
  adc fData
  tax
  lda f:$03d400,x
  sta fuStep
  lda $36
  asl
  clc
  adc fData
  adc #512
  tax
  lda f:$03d400,x
  sta fvStep
  stz fuStart
  stz fv
  lda fAsset
  asl
  tax
  lda $3c
  bit #$10
  beq :+
  lda f:flip_dimensions,x
  and #255
  xba
  dec
  sta fuStart
  lda fuStep
  eor #$ffff
  inc
  sta fuStep
:
  lda $3c
  bit #$20
  beq :+
  lda f:flip_dimensions+1,x
  and #255
  xba
  dec
  sta fv
  lda fvStep
  eor #$ffff
  inc
  sta fvStep
:
  lda fAsset
  asl
  asl
  asl
  clc
  adc fAsset
  sta fData
  lda $3c
  and #3
  cmp #3
  bcc :+
  lda #0
:
  sta fPixel
  asl
  clc
  adc fPixel
  adc fData
  tax
  lda f:flip_sources,x
  sta fData
  lda #1
  sta fSource+2
  lda $0102
  and #255
  sta fDest+2
  lda fAsset
  xba
  lsr
  sta fAsset
  stz fDy
flip_row:
  lda $3a
  clc
  adc fDy
  cmp #192
  jcs flip_next_row
  .repeat 7
    asl
  .endrepeat
  clc
  adc $019a
  sta fRow
  lda fv
  xba
  and #255
  asl
  clc
  adc fAsset
  tax
  lda f:flip_rows,x
  clc
  adc fData
  sta fSource
  lda fuStart
  sta fu
  stz fDx
flip_pixel:
  lda $38
  clc
  adc fDx
  cmp #256
  jcs flip_next_pixel
  sta fScreenX
  lsr
  clc
  adc fRow
  sta fDest
  lda fu
  xba
  and #255
  lsr
  tay
  lda [fSource],y
  bcc :+
  .repeat 4
    lsr
  .endrepeat
:
  and #15
  beq flip_next_pixel
  sta fPixel
  lda fScreenX
  lsr
  sep #$20
  bcs flip_high_pixel
  lda [fDest]
  and #$f0
  ora fPixel
  sta [fDest]
  bra flip_pixel_done
flip_high_pixel:
  lda fPixel
  .repeat 4
    asl
  .endrepeat
  sta fPixel
  lda [fDest]
  and #15
  ora fPixel
  sta [fDest]
flip_pixel_done:
  rep #$20
flip_next_pixel:
  lda fu
  clc
  adc fuStep
  sta fu
  inc fDx
  lda fDx
  cmp $34
  jne flip_pixel
flip_next_row:
  lda fv
  clc
  adc fvStep
  sta fv
  inc fDy
  lda fDy
  cmp $36
  jne flip_row
  rtl

flip_sources:
.include "flip_sources.inc"
flip_dimensions:
.incbin "flip_dimensions.bin"
flip_rows:
.incbin "flip_rows.bin"
flip_pixels:
.incbin "flip_pixels.bin"
