; Shared map changes only at presentation; each record owns its map/list.
.segment "GSU"
fd_bases:
  .repeat 8,I
  .word fdStorage+1472*I
  .endrepeat
.segment "GSU"
.export fd_collect, fd_flip, fd_flip_done
.a16
.i16
fd_collect:
  phx
  txa
  .repeat 8
    lsr
  .endrepeat
  tax
  lda f:fd_bases,x
  sta f:$002181
  lda f:$434660
  pha
  bmi fd_collect_full
  asl
  sta f:$004305
  lda f:$434660
  asl
  asl
  asl
  sta fdMask
  asl
  asl
  asl
  clc
  adc fdMask
  adc #300
  sta fdCost
  lda f:$004305
  beq fd_collect_done
  bra fd_collect_dma
fd_collect_full:
  lda #2000
  sta fdCost
  lda #1472
  sta f:$004305
fd_collect_dma:
  lda #$4000
  sta f:$004302
  lda #$8000
  sta f:$004300
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
fd_collect_done:
  pla
  plx
  sta pipe_records+62,x
  lda fdCost
  sta pipe_records+60,x
  rtl

fd_flip:
  phx
  lda pipe_records+62,x
  jeq fd_flip_done
  bmi fd_flip_full
  tay
  txa
  .repeat 8
    lsr
  .endrepeat
  tax
  lda f:fd_bases,x
  tax
fd_flip_item:
  lda a:$0000,x
  pha
  and #$7fff
  clc
  adc #$5e00
  sta f:$002116
  pla
  bpl fd_flip_hide
  and #$7fff
  sec
  sbc #31
  ora #$2400
  bra fd_flip_store
fd_flip_hide:
  lda #$2400
fd_flip_store:
  sta f:$002118
  inx
  inx
  dey
  bne fd_flip_item
  bra fd_flip_done
fd_flip_full:
  txa
  .repeat 8
    lsr
  .endrepeat
  tax
  lda f:fd_bases,x
  sta f:$004302
  lda #1472
  sta f:$004305
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  lda #$1801
  sta f:$004300
  lda #$5e20
  sta f:$002116
  sep #$20
  lda #$80
  sta f:$002115
  lda #$7e
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
fd_flip_done:
  plx
  rtl
