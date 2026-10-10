; CHRだけを4面へ先行転送し、共有マップは表示世代と同時に更新する。
.setcpu "65816"
.smart
.import pipe_records, fx4_dma_bytes
.export four_map_collect: far, four_map_flip: far
.segment "GSU"
.a16
.i16
four_map_collect:
  rep #$30
  lda pipe_records+2,x
  sec
  sbc #6
  sta pipe_records+2,x
  lda pipe_records+34,x
  sec
  sbc #1472
  sta pipe_records+34,x
  rtl
four_map_flip:
  php
  phx
  rep #$30
  lda pipe_records,x
  and #$8400
  clc
  adc #$6040
  sta f:$004302
  lda #1472
  sta f:$004305
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  lda #$1801
  sta f:$004300
  lda #$6020
  sta f:$002116
  sep #$20
  lda #$80
  sta f:$002115
  lda #$95
  sta f:$002231
  lda pipe_records,x
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
  plx
  plp
  rtl
