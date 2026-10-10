pipe_background_reserve:
  rep #$30
  lda pipe_presented_irq
  bne bg_cpu_reserve_done
  lda pipe_target_slot
  cmp #$ffff
  beq bg_cpu_reserve_done
  phx
  ldx pipe_record_offset
  lda pipe_records+42,x
  cmp pipe_background_version
  beq bg_cpu_reserve_same
  plx
  lda pipe_available
  sec
  sbc #2300
  bpl :+
  lda #0
:
  sta pipe_available
  rts
bg_cpu_reserve_same:
  plx
bg_cpu_reserve_done:
  rts

pipe_background_upload:
  rep #$30
  lda pipe_records+42,x
  cmp pipe_background_version
  jeq bg_cpu_upload_done
  sta pipe_background_version
  lda pipe_records+40,x
  sta f:$002232
  sta f:$004302
  sta pipe_background_source
  lda #$02e0
  sta f:$002235
  lda #$1801
  sta f:$004300
  lda #$65c0
  sta f:$002116
  lda #640
  sta f:$004305
  sep #$20
  lda #$43
  sta f:$002234
  sta f:$004304
  lda #$15
  sta f:$002231
  lda #1
  sta f:$00420b
  rep #$20
  lda pipe_background_source
  clc
  adc #640
  sta f:$004302
  lda #$6740
  sta f:$002116
  lda #384
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  lda pipe_background_source
  clc
  adc #1024
  sta f:$004302
  lda #$7480
  sta f:$002116
  lda #1024
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  lda pipe_background_source
  sep #$20
  lda #$95
  sta f:$002231
  rep #$30
bg_cpu_upload_done:
  rts
