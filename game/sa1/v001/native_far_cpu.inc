; BG2は共有mapのrow24/25だけを、遠景の14行に限定して表示する。
; channel7はMode1で未使用だったBG4 HOFSからTMへ切り替える。
pipe_native_far_update:
  rep #$30
  txa
  clc
  adc #pipe_records+48
  sta f:$7e1d0c
  .if .defined(SA1_NATIVE_BACKGROUND) && !.defined(SA1_NATIVE_NEAR)
  jsr pipe_background_upload
  .endif
  sep #$20
  .if .defined(SA1_NATIVE_BACKGROUND) && !.defined(SA1_NATIVE_NEAR)
  lda #0
  sta f:$00210f
  sta f:$00210f
  .else
  lda pipe_records+10,x
  sta f:$00210f
  lda pipe_records+11,x
  sta f:$00210f
  .endif
  rep #$20
  lda #102
  sec
  sbc pipe_records+14,x
  sta pipe_dma_chunk
  sep #$20
  lda pipe_dma_chunk
  sta f:$002110
  lda pipe_dma_chunk+1
  sta f:$002110
  rep #$20
  lda pipe_records+14,x
  clc
  adc #89
  cmp #203
  bcs native_far_hidden
  cmp #128
  bcc native_far_short
  sec
  sbc #127
  ora #$1500
  sta pipe_records+50,x
  lda #$157f
  sta pipe_records+48,x
  lda #$170e
  sta pipe_records+52,x
  lda #$1501
  sta pipe_records+54,x
  stz pipe_records+56,x
  rts
native_far_short:
  ora #$1500
  sta pipe_records+48,x
  lda #$170e
  sta pipe_records+50,x
  lda #$1501
  sta pipe_records+52,x
  stz pipe_records+54,x
  rts
native_far_hidden:
  lda #$1501
  sta pipe_records+48,x
  stz pipe_records+50,x
  rts
