; マップの低byteは全量、高byteは新旧の25領域の和だけ送る。
.setcpu "65816"
.smart
.macpack longbranch
.import pipe_records, pipe_record_offset, pipe_available, fx4_dma_bytes
.export split_map_collect: far, split_map_prepare: far
.export split_map_transfer: far, split_map_try: far
.segment "COLORBSS"
split_old: .res 12
split_page: .res 2
split_begin: .res 2
split_end: .res 2
split_bytes: .res 2
split_source: .res 2
split_descriptor: .res 2
.segment "GSU"
.a16
.i16
split_map_collect:
  php
  phx
  rep #$30
  lda #$8000
  sta f:$004300
  lda #4
  sta f:$004305
  lda pipe_records,x
  and #$8400
  clc
  adc #$66c0
  sta f:$004302
  txa
  clc
  adc #pipe_records+60
  sta f:$002181
  sep #$20
  lda #0
  sta f:$002183
  lda pipe_records,x
  sta f:$004304
  lda #$95
  sta f:$002231
  lda #1
  sta f:$00420b
  rep #$30
  plx
  plp
  rtl

split_map_prepare:
  php
  phx
  phy
  rep #$30
  lda pipe_records+6,x
  xba
  and #255
  lsr
  lsr
  lsr
  sta split_page
  tay
  lda #736
  sta split_begin
  stz split_end
  lda pipe_records+62,x
  beq split_no_current
  sta split_end
  lda pipe_records+60,x
  sta split_begin
split_no_current:
  lda split_old+2,y
  beq split_range_ready
  cmp split_end
  bcc :+
  sta split_end
:
  lda split_old,y
  cmp split_begin
  bcs split_range_ready
  sta split_begin
split_range_ready:
  lda split_end
  beq split_no_high
  sec
  sbc split_begin
split_no_high:
  clc
  adc #736
  sta split_bytes
  lda pipe_records+2,x
  sec
  sbc #6
  clc
  adc pipe_record_offset
  adc #208
  tay
  lda pipe_records+34,x
  sec
  sbc pipe_records,y
  clc
  adc split_bytes
  sta pipe_records+34,x
  lda split_bytes
  sta pipe_records,y
  sty split_descriptor
  lda pipe_records+2,y
  sta split_source
  ply
  plx
  plp
  rtl

split_map_try:
  rep #$30
  lda split_bytes
  sta split_end
  lsr
  lsr
  lsr
  clc
  adc split_end
  adc #576
  cmp pipe_available
  bcs split_map_defer
  lda split_bytes
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  jsl split_map_transfer
  rep #$30
  ldx pipe_record_offset
  lda pipe_records+2,x
  sta pipe_records+4,x
  stz pipe_records+34,x
  sec
  rtl
split_map_defer:
  clc
  rtl

split_map_transfer:
  rep #$30
  ldx pipe_record_offset
  sep #$20
  lda #$95
  sta f:$002231
  lda pipe_records,x
  sta f:$004304
  lda #0
  sta f:$002115
  rep #$20
  lda #$1800
  sta f:$004300
  lda split_source
  sta f:$004302
  lda #736
  sta f:$004305
  lda pipe_records+6,x
  clc
  adc #$0420
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  lda #$80
  sta f:$002115
  rep #$20
  lda split_bytes
  sec
  sbc #736
  beq split_high_done
  sta f:$004305
  lda split_source
  clc
  adc #736
  adc split_begin
  sta f:$004302
  lda #$1900
  sta f:$004300
  lda pipe_records+6,x
  clc
  adc #$0420
  adc split_begin
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
split_high_done:
  lda #$1801
  sta f:$004300
  ldy split_page
  lda pipe_records+60,x
  sta split_old,y
  lda pipe_records+62,x
  sta split_old+2,y
  rtl
