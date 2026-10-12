; global dirty範囲を左右の中央128pxへ写し、可視部分だけを消去する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_stack_clear_prepare: far, sa1_stack_clear_band: far
.import sa1_dma_try_begin: far, sa1_dma_end: far
.import sa1_clear_wide_band: far
.export sa1_split_clear: far
.ifndef SA1_SPLIT_WIDE_CLEAR_MIN
SA1_SPLIT_WIDE_CLEAR_MIN=128
.endif
.segment "GSU"
sa1_split_clear:
  rep #$30
  jsl sa1_stack_clear_prepare
  stz $01b2
split_clear_band:
  lda $01b2
  asl
  asl
  tax
  lda $0120,x
  sta $01b4
  lda $0122,x
  sta $01b6
  cmp $01b4
  jcc split_clear_next
  jeq split_clear_next
  lda $01b2
  xba
  asl
  asl
  clc
  adc #$0400
  sta $01b8
  lda $01b4
  cmp #64
  bcs split_clear_right
  lda $01b6
  cmp #64
  bcc :+
  lda #64
:
  sec
  sbc $01b4
  sta $ea
  lda $01b8
  clc
  adc #32
  adc $01b4
  sta $e6
  jsr split_clear_region
split_clear_right:
  lda $01b6
  cmp #65
  bcc split_clear_next
  lda $01b4
  cmp #64
  bcs :+
  lda #64
:
  sta $ec
  lda $01b6
  sec
  sbc $ec
  sta $ea
  lda $01b8
  clc
  adc #$8000-32
  adc $ec
  sta $e6
  jsr split_clear_region
split_clear_next:
  inc $01b2
  lda $01b2
  cmp #24
  jcc split_clear_band
  rtl
split_clear_region:
  lda #8
  sta $e8
  jsl sa1_dma_try_begin
  bcs split_clear_dma
  jsl sa1_stack_clear_band
  rts
split_clear_dma:
  lda $ea
  cmp #SA1_SPLIT_WIDE_CLEAR_MIN
  bcc split_clear_narrow
  jsl sa1_clear_wide_band
  jsl sa1_dma_end
  rts
split_clear_narrow:
  sep #$20
  lda #$84
  sta $2230
  lda #2
  sta $2234
  rep #$20
split_clear_scanline:
  lda $ea
  sta $2238
  lda #$8000
  sta $2232
  lda $e6
  sta $2235
  sep #$20
  lda $0102
  sta $2237
  rep #$20
  lda $e6
  clc
  adc #128
  sta $e6
  dec $e8
  bne split_clear_scanline
  jsl sa1_dma_end
  rts
