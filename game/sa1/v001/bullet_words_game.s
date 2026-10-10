.setcpu "65816"
.smart
.macpack longbranch
.export sa1_bullet_cache_init: far, sa1_bullet_cache_prepare: far
.import sa1_dma_try_begin: far, sa1_dma_end: far
.import __BULLETJIT_LOAD__, __BULLETJIT_SIZE__
.segment "GSU"
cSize=$dc
cRead=$b6
cRows=$a6
cStep=$b8
cV=$ba
cDy=$bc
cStart=$da
cRecord=$aa
cOrigin=$d4
cCount=$d6
cValue=$d2
cMask=$d0
cBase=$ae
sa1_bullet_cache_init:
  rtl
sa1_bullet_cache_prepare:
  rep #$30
  lda $3e
  cmp #6
  bcc words_other
  cmp #9
  bcc words_select
  cmp #37
  beq words_select
words_other:
  clc
  rtl
words_select:
  ; phase×12 + hflip×6 + parity×3
  lda $3c
  and #3
  cmp #3
  bcc :+
  lda #0
:
  asl
  sta cSize
  asl
  clc
  adc cSize
  asl
  sta cSize
  lda $3c
  and #$10
  lsr
  lsr
  lsr
  sta cRead
  lda $38
  and #1
  clc
  adc cRead
  sta cRead
  asl
  clc
  adc cRead
  adc cSize
  sta cRead
  lda $2c
  asl
  tax
  lda f:$433000,x
  tax
  lda f:$ff0001,x
  clc
  adc cRead
  tax
  lda f:$ff0000,x
  sta cRows
  sep #$20
  lda f:$ff0002,x
  sta cRows+2
  rep #$20
  lda $3e
  sec
  sbc #6
  cmp #3
  bcc :+
  lda #3
:
  pha
  xba
  asl
  asl
  sta cSize
  lda $36
  asl
  clc
  adc cSize
  adc #512
  tax
  lda f:$03d400,x
  sta cStep
  stz cV
  pla
  asl
  tax
  lda $3c
  bit #$20
  beq :+
  lda f:cache_dimensions+1,x
  and #255
  xba
  dec
  sta cV
  lda cStep
  eor #$ffff
  inc
  sta cStep
:

  stz cDy
  jsl sa1_dma_try_begin
  bcc words_copy_cpu
  lda #__BULLETJIT_SIZE__
  sta $2238
  lda #.loword(__BULLETJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__BULLETJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  jml words_enter
words_copy_cpu:
  phb
  ldx #.loword(__BULLETJIT_LOAD__)
  ldy #$0300
  lda #__BULLETJIT_SIZE__-1
  mvn #$01,#$00
  plb
  jml words_enter
.segment "BULLETJIT"
words_enter:
  lda $019a
  sta cBase
  phb
  sep #$20
  lda $0102
  pha
  plb
words_row:
  rep #$30
  lda cDy
  clc
  adc $3a
  cmp #192
  jcs words_next_row
  .repeat 7
    asl
  .endrepeat
  clc
  adc cBase
  sta cStart
  lda cV
  xba
  and #255
  sta cRead
  asl
  clc
  adc cRead
  tay
  lda [cRows],y
  sta cRecord
  iny
  iny
  sep #$20
  lda [cRows],y
  sta cRecord+2
  rep #$20
  ldy #2
  lda [cRecord],y
  and #255
  clc
  adc $48
  sta cOrigin
  iny
  lda [cRecord],y
  and #255
  sta cCount
  lda #4
  sta cRead
  lda cCount
  jeq words_next_row
  asl
  clc
  adc cOrigin
  cmp #129
  bcs words_word
  lda cOrigin
  bmi words_word
  clc
  adc cStart
  tax
  ldy #4
words_interior:
  lda [cRecord],y
  beq words_interior_next
  bit #$000f
  beq words_interior_masked
  bit #$00f0
  beq words_interior_masked
  bit #$0f00
  beq words_interior_masked
  bit #$f000
  beq words_interior_masked
  sta a:$0000,x
  bra words_interior_next
words_interior_masked:
  sta cValue
  phx
  and #255
  tax
  lda f:cache_masks,x
  and #255
  sta cMask
  lda cValue
  xba
  and #255
  tax
  lda f:cache_masks,x
  and #255
  xba
  ora cMask
  plx
  and a:$0000,x
  ora cValue
  sta a:$0000,x
words_interior_next:
  iny
  iny
  inx
  inx
  dec cCount
  bne words_interior
  jmp words_next_row
words_word:
  lda cCount
  jeq words_next_row
  lda cOrigin
  cmp #128
  bcc words_visible
  cmp #$ffff
  beq words_visible
  jmp words_next_word
words_visible:
  ldy cRead
  lda [cRecord],y
  sta cValue
  jeq words_next_word
  and #255
  tax
  lda f:cache_masks,x
  and #255
  sta cMask
  lda cValue
  xba
  and #255
  tax
  lda f:cache_masks,x
  and #255
  xba
  ora cMask
  sta cMask
  lda cStart
  clc
  adc cOrigin
  tax
  lda cOrigin
  cmp #127
  beq words_last_byte
  cmp #$ffff
  beq words_first_byte
  lda a:$0000,x
  and cMask
  ora cValue
  sta a:$0000,x
  bra words_next_word
words_last_byte:
  sep #$20
  lda a:$0000,x
  and cMask
  ora cValue
  sta a:$0000,x
  rep #$20
  bra words_next_word
words_first_byte:
  inx
  sep #$20
  lda a:$0000,x
  and cMask+1
  ora cValue+1
  sta a:$0000,x
  rep #$20
words_next_word:
  inc cRead
  inc cRead
  inc cOrigin
  inc cOrigin
  dec cCount
  jmp words_word
words_next_row:
  lda cV
  clc
  adc cStep
  sta cV
  inc cDy
  lda cDy
  cmp $36
  jne words_row
  plb
  sec
  rtl
.segment "GSU"
cache_dimensions:
.incbin "flip_dimensions.bin"
cache_masks:
.repeat 256, I
  .byte ((I & 15)=0)*15 | ((I & 240)=0)*240
.endrepeat
