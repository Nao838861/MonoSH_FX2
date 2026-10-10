.setcpu "65816"
.smart
.macpack longbranch
.export sa1_sparse_map_prepare: far
.import sa1_dma_try_begin: far, sa1_dma_end: far
.segment "GSU"
smMap=$a0
smBank=$a2
smDesc=$a4
smEnd=$a6
smTile=$a8
smCount=$aa
smPointer=$ac
sa1_sparse_map_prepare:
  rep #$30
  lda $019a
  clc
  adc #$6040
  sta smMap
  lda $0102
  and #255
  sta smBank
  sta smPointer+2
  lda smMap
  sta smPointer
  jsl sa1_dma_try_begin
  bcc sm_fill_cpu
  lda #1472
  sta $2238
  lda #.loword(sm_empty_map)
  sta $2232
  sep #$20
  lda #^sm_empty_map
  sta $2234
  lda #$84
  sta $2230
  rep #$20
  lda smMap
  sta $2235
  sep #$20
  lda smBank
  sta $2237
  rep #$20
  jsl sa1_dma_end
  bra sm_map_ready
sm_fill_cpu:
  ldy #0
  lda #$2420
sm_fill_word:
  sta [smPointer],y
  iny
  iny
  cpy #1472
  bcc sm_fill_word
sm_map_ready:
  lda $011a
  asl
  sta smEnd
  asl
  clc
  adc smEnd
  sta smEnd
  stz smDesc
  lda #$2421
  sta smTile
sm_descriptor:
  ldx smDesc
  cpx smEnd
  bcs sm_done
  lda f:$430800,x
  .repeat 5
    lsr
  .endrepeat
  sta smCount
  lda f:$430804,x
  .repeat 3
    lsr
  .endrepeat
  sec
  sbc #64
  tay
  lda smTile
sm_tile:
  sta [smPointer],y
  inc
  iny
  iny
  dec smCount
  bne sm_tile
  sta smTile
  lda smDesc
  clc
  adc #6
  sta smDesc
  bra sm_descriptor
sm_done:
  rtl
sm_empty_map:
.repeat 736
  .word $2420
.endrepeat
