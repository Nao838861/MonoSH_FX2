; raw七面の前の占有タイルだけを消す。空白のタイルは最初から零のまま。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_stack_clear_prepare: far,sa1_stack_clear_band: far
.import sa1_dma_try_begin: far,sa1_dma_end: far
.import tm_first: far,tm_length: far,tm_rest: far
.ifndef SA1_MASK_CLEAR_GAP
SA1_MASK_CLEAR_GAP=0
.endif
.export sa1_mask_history: far,sa1_mask_clear: far
.segment "GSU"
mhTemp=$b0
mhPtr=$b4
sa1_mask_history:
  rep #$30
  pha
  lda $0116
  cmp #1
  bne mh_initialized
  lda #0
  ldx #670
mh_init:
  sta f:$432300,x
  dex
  dex
  bpl mh_init
mh_initialized:
  pla
  .repeat 5
    asl
  .endrepeat
  sta mhTemp
  asl
  clc
  adc mhTemp
  adc #$2300
  sta mhPtr
  sep #$20
  lda #$43
  sta mhPtr+2
  rep #$20
  ldx #0
  ldy #0
mh_copy:
  lda [mhPtr],y
  sta f:$432600,x
  lda f:$432800,x
  sta [mhPtr],y
  inx
  inx
  iny
  iny
  cpx #96
  bcc mh_copy
  rtl

scRow=$a0
scLo=$a2
scHi=$a4
scBit=$a6
scStart=$a8
scActive=$aa
scOffset=$ac
scEnd=$ae
scByte=$b0
scMask=$b2
scFirst=$b4
scNextEnd=$b6
sa1_mask_clear:
  rep #$30
  jsl sa1_stack_clear_prepare
  stz scRow
  stz $01ac
sc_band:
  ldx scRow
  lda f:$432600,x
  sta scLo
  lda f:$432602,x
  sta scHi
.if SA1_MASK_CLEAR_GAP > 0
  lda scLo
  sta $b0
  sta $bc
  lda scHi
  sta $b2
  sta $be
  .repeat SA1_MASK_CLEAR_GAP
    asl $bc
    rol $be
    lda $bc
    ora $b0
    sta $b0
    lda $be
    ora $b2
    sta $b2
  .endrepeat
  lda $b0
  sta $b4
  lda $b2
  sta $b6
  .repeat SA1_MASK_CLEAR_GAP
    lsr $b2
    ror $b0
    lda $b0
    and $b4
    sta $b4
    lda $b2
    and $b6
    sta $b6
  .endrepeat
  lda $b4
  ora scLo
  sta scLo
  lda $b6
  ora scHi
  sta scHi
.endif
  txa
  xba
  clc
  adc $019a
  sta scOffset
  stz scBit
  stz scActive
.ifdef SA1_MASK_CLEAR_TABLE
  stz scByte
sc_byte:
  ldx scByte
  lda scLo,x
  and #255
  sta scMask
  beq sc_next_byte
sc_run:
  lda scMask
  asl
  tax
  lda f:tm_first,x
  .repeat 5
    lsr
  .endrepeat
  pha
  lda scByte
  asl
  asl
  asl
  sta scFirst
  pla
  clc
  adc scFirst
  sta scFirst
  lda f:tm_length,x
  .repeat 5
    lsr
  .endrepeat
  clc
  adc scFirst
  sta scNextEnd
  ldx scMask
  lda f:tm_rest,x
  and #255
  sta scMask
  lda scActive
  beq sc_new_run
  lda scEnd
  cmp scFirst
  beq sc_extend
  sta scBit
  jsr sc_flush
sc_new_run:
  lda scFirst
  sta scStart
  lda #1
  sta scActive
sc_extend:
  lda scNextEnd
  sta scEnd
  lda scMask
  bne sc_run
sc_next_byte:
  inc scByte
  lda scByte
  cmp #4
  bcc sc_byte
  lda scEnd
  sta scBit
  bra sc_finish
.else
sc_bit:
  lda scLo
  ora scHi
  beq sc_finish
  lsr scHi
  ror scLo
  bcc sc_off
  lda scActive
  bne sc_next_bit
  lda scBit
  sta scStart
  inc scActive
  bra sc_next_bit
sc_off:
  lda scActive
  beq sc_next_bit
  jsr sc_flush
  stz scActive
sc_next_bit:
  inc scBit
  lda scBit
  cmp #32
  bcc sc_bit
.endif
sc_finish:
  lda scActive
  beq sc_next_band
  jsr sc_flush
sc_next_band:
  lda scRow
  clc
  adc #4
  sta scRow
  cmp #96
  jcc sc_band
  rtl
sc_flush:
  lda scBit
  sec
  sbc scStart
  asl
  asl
  sta $ea
  asl
  asl
  asl
  clc
  adc $01ac
  sta $01ac
  lda scStart
  asl
  asl
  clc
  adc scOffset
  sta $e6
.ifdef SA1_MASK_CLEAR_DMA
  jsl sa1_dma_try_begin
  bcc sc_stack
  sep #$20
  lda #$84
  sta $2230
  lda #3
  sta $2234
  rep #$20
  lda #$f000
  sta $2232
  ldx #8
sc_dma_line:
  lda $ea
  sta $2238
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
  dex
  bne sc_dma_line
  jsl sa1_dma_end
  rts
sc_stack:
.endif
  jsl sa1_stack_clear_band
  rts
