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
cOpaque=$b0
cLastShape=$e0
cShape=$e2
cLength=$e4
cPrefix=$e6
cFirst=$ea
cLast=$ec
cClipTarget=$f0
cPatch=$f2
cSaved=$f4
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
  .ifdef SA1_BULLET_SHAPES
  rep #$30
  lda #$ffff
  sta cLastShape
  .endif
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
  .ifdef SA1_BULLET_OPACITY
  lda [cRecord]
  .ifdef SA1_BULLET_SHAPES
  sta cShape
  .else
  sta cOpaque
  .endif
  .endif
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
  .ifdef SA1_BULLET_SHAPES
  jsl words_shape_clipped
  jmp words_next_row
  .endif
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
  .ifdef SA1_BULLET_SHAPES
  jsl words_shape_draw
  jmp words_next_row
  .endif
  .ifdef SA1_BULLET_OPAQUE8
  jmp words_opaque8
  .endif
words_interior:
  .ifdef SA1_BULLET_OPACITY
  lsr cOpaque
  .endif
  lda [cRecord],y
  beq words_interior_next
  .ifdef SA1_BULLET_OPACITY
  bcc words_interior_masked
  .else
  bit #$000f
  beq words_interior_masked
  bit #$00f0
  beq words_interior_masked
  bit #$0f00
  beq words_interior_masked
  bit #$f000
  beq words_interior_masked
  .endif
  sta a:$0000,x
  bra words_interior_next
words_interior_masked:
  sta cValue
  .ifdef SA1_BULLET_MASK_ARITHMETIC
  ; 各nibbleの0だけを$Fにする。加算はnibble間のcarryを起こさない。
  and #$7777
  clc
  adc #$7777
  ora cValue
  eor #$ffff
  and #$8888
  sta cMask
  lsr
  ora cMask
  sta cMask
  lsr
  lsr
  ora cMask
  .else
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
  .endif
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
  .ifdef SA1_BULLET_OPACITY
  lsr cOpaque
  .endif
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
  .ifdef SA1_BULLET_MASK_ARITHMETIC
  and #$7777
  clc
  adc #$7777
  ora cValue
  eor #$ffff
  and #$8888
  sta cMask
  lsr
  ora cMask
  sta cMask
  lsr
  lsr
  ora cMask
  .else
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
  .endif
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
  .ifdef SA1_BULLET_LEFT_FAST
  ; 左端の不完全なwordを抜けたら、残りは画面内の高速ループへ戻す。
  jeq words_next_row
  lda cOrigin
  jmi words_word
  cmp #128
  jcs words_next_row
  lda cCount
  asl
  clc
  adc cOrigin
  cmp #129
  jcs words_word
  lda cOrigin
  clc
  adc cStart
  tax
  ldy cRead
  jmp words_interior
  .endif
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
  .ifdef SA1_BULLET_OPAQUE8
words_opaque8:
  ; headerの8bitが全て立つ連続16byteだけを判定・反復なしで写す。
  lda cOpaque
  and #255
  cmp #255
  jne words_interior
  .repeat 8
    lda [cRecord],y
    sta a:$0000,x
    iny
    iny
    inx
    inx
  .endrepeat
  lda cOpaque
  xba
  and #255
  sta cOpaque
  lda cCount
  sec
  sbc #8
  sta cCount
  jeq words_next_row
  jmp words_interior
  .endif
.segment "GSU"
  .ifdef SA1_BULLET_SHAPES
words_shape_draw:
  .ifdef SA1_BULLET_SHAPES_ROM
  lda cLast
  cmp cCount
  jne shape_iram_draw
  lda cShape
  clc
  adc #3
  sta f:$0007d1
  lda cFirst
  beq shape_rom_begin
  ldx cShape
  lda f:$c30000,x
  and #255
  clc
  adc cShape
  adc #3
  sta cPrefix
  sep #$20
  lda #$c3
  sta cPrefix+2
  rep #$20
  ldy cFirst
  lda [cPrefix],y
  and #255
  clc
  adc f:$0007d1
  sta f:$0007d1
shape_rom_begin:
  sep #$20
  lda #$c3
  sta f:$0007d3
  lda #$5c
  sta f:$0007d0
  rep #$20
  lda cFirst
  asl
  clc
  adc #4
  tay
  lda cStart
  clc
  adc cOrigin
  tax
  jsl $0007d0
  rtl
shape_iram_draw:
  .endif
  phx
  phy
  phb
  sep #$20
  lda #0
  pha
  plb
  rep #$30
  lda cShape
  cmp cLastShape
  beq words_shape_ready
  sta cLastShape
  tax
  lda f:$c30000,x
  and #255
  sta cLength
  jsl sa1_dma_try_begin
  bcc words_shape_cpu
  lda cLength
  sta $2238
  lda cShape
  clc
  adc #3
  sta $2232
  sep #$20
  lda #$c3
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0500
  sta $2235
  jsl sa1_dma_end
  bra words_shape_ready
words_shape_cpu:
  lda cShape
  clc
  adc #3
  tax
  ldy #$0500
  lda cLength
  dec
  mvn #$c3,#$00
words_shape_ready:
  plb
  ply
  plx
  lda cFirst
  bne shape_draw_slice
  lda cLast
  cmp cCount
  bne shape_draw_slice
  lda cStart
  clc
  adc cOrigin
  tax
  ldy #4
  jsl $000500
  rtl
shape_draw_slice:
  lda cShape
  clc
  adc #3
  adc cLength
  sta cPrefix
  sep #$20
  lda #$c3
  sta cPrefix+2
  rep #$20
  ldy cFirst
  lda [cPrefix],y
  and #255
  clc
  adc #$0500
  sta f:$0007d1
  sep #$20
  lda #0
  sta f:$0007d3
  lda #$5c
  sta f:$0007d0
  rep #$20
  ldy cLast
  lda [cPrefix],y
  and #255
  clc
  adc #$0500
  sta cPatch
  tax
  sep #$20
  lda f:$000000,x
  sta cSaved
  lda #$6b
  sta f:$000000,x
  rep #$20
  lda cFirst
  asl
  clc
  adc #4
  tay
  lda cStart
  clc
  adc cOrigin
  tax
  jsl $0007d0
  ldx cPatch
  sep #$20
  lda cSaved
  sta f:$000000,x
  rep #$30
  rtl
words_shape_clipped:
  rep #$30
  lda cOrigin
  cmp #128
  bcc shape_left_inside
  cmp #$8000
  jcc shape_clip_done
  lda cCount
  asl
  clc
  adc cOrigin
  jmi shape_clip_done
  jeq shape_clip_done
  lda cOrigin
  eor #$ffff
  inc
  inc
  lsr
  sta cFirst
  bra shape_left_ready
shape_left_inside:
  stz cFirst
shape_left_ready:
  lda #128
  sec
  sbc cOrigin
  lsr
  cmp cCount
  bcc :+
  lda cCount
:
  sta cLast
  cmp cFirst
  beq shape_clip_edges
  jsl words_shape_draw
shape_clip_edges:
  lda cOrigin
  bpl shape_right_edge
  bit #1
  beq shape_right_edge
  lda cFirst
  asl
  clc
  adc #3
  tay
  lda cStart
  sta cClipTarget
  jsr shape_edge_byte
shape_right_edge:
  lda cOrigin
  bit #1
  beq shape_clip_done
  lda cLast
  cmp cCount
  bcs shape_clip_done
  asl
  clc
  adc #4
  tay
  lda cStart
  clc
  adc #127
  sta cClipTarget
  jsr shape_edge_byte
shape_clip_done:
  rtl
shape_edge_byte:
  lda [cRecord],y
  and #255
  beq shape_edge_done
  sta cValue
  tax
  lda f:cache_masks,x
  and #255
  sta cMask
  ldx cClipTarget
  sep #$20
  lda a:$0000,x
  and cMask
  ora cValue
  sta a:$0000,x
  rep #$30
shape_edge_done:
  rts
  .endif
cache_dimensions:
.incbin "flip_dimensions.bin"
cache_masks:
.repeat 256, I
  .byte ((I & 15)=0)*15 | ((I & 240)=0)*240
.endrepeat
