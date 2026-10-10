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
.ifdef SA1_VRAM_FIFO
  lda f:$0031a2
  .repeat 4
    asl
  .endrepeat
  sta pipe_records+6,x
  lda f:$0031a4
  sta pipe_records+38,x
  lda f:$0031a6
  sta pipe_records+36,x
.ifdef SA1_FIFO_MAP_BW
  lda f:$0031a8
  sta pipe_records+60,x
  lda f:$0031aa
  sta pipe_records+62,x
.endif
.ifdef SA1_FIFO_ARCHIVE
  phx
  txa
  .repeat 8
    lsr
  .endrepeat
  tax
  lda f:fifo_map_bases,x
  plx
  sta pipe_records+60,x
.ifdef SA1_FIFO_CPU_MAP
  stz pipe_records+62,x
.else
  sta f:$002181
  lda pipe_records,x
  and #$8400
  clc
  adc #$6040
  sta f:$004302
  lda #1472
  sta f:$004305
  lda #$8000
  sta f:$004300
  sep #$20
  lda #1
  sta f:$002183
  lda pipe_records,x
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
.endif
.endif
.else
  lda pipe_records+2,x
  sec
  sbc #6
  sta pipe_records+2,x
  lda pipe_records+34,x
  sec
  sbc #1472
  sta pipe_records+34,x
.endif
  rtl
four_map_flip:
  php
  phx
  rep #$30
.if .defined(SA1_FIFO_ARCHIVE) || .defined(SA1_FIFO_MAP_BW)
  lda pipe_records+60,x
.else
  lda pipe_records,x
  and #$8400
  clc
  adc #$6040
.endif
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
.ifdef SA1_FIFO_ARCHIVE
  lda #$7f
.else
.ifdef SA1_FIFO_MAP_BW
  lda pipe_records+62,x
.else
  lda pipe_records,x
.endif
.endif
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
  plx
  plp
  rtl
.ifdef SA1_FIFO_ARCHIVE
fifo_map_bases:
  .repeat 12,I
    .word $a000+1472*I
  .endrepeat
.endif
.ifdef SA1_FIFO_MAP_BW
.export fifo_bw_map_bases: far
fifo_bw_map_bases:
  .word $6c00,$40,$71c0,$40,$6c00,$41,$71c0,$41,$6c00,$42,$71c0,$42
  .word $ec00,$40,$f1c0,$40,$ec00,$41,$f1c0,$41,$ec00,$42,$f1c0,$42
.endif
