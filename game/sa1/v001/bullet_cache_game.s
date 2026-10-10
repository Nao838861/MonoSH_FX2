; 敵弾の縮小済み行からnative codeを生成し、65KiBのBW-RAMへ保持する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_bullet_cache_init: far, sa1_bullet_cache_prepare: far
.export cache_miss: far, cache_ready: far
.import sa1_dma_try_begin: far, sa1_dma_end: far
.import __BULLETJIT_LOAD__, __BULLETJIT_SIZE__
.segment "GSU"
cWH=$a0
cAF=$a2
cMeta=$a4
cRows=$a6
cRecord=$aa
cProgram=$ae
cOut=$b2
cRead=$b6
cStep=$b8
cV=$ba
cDy=$bc
cOffset=$be
cMask=$d0
cValue=$d2
cOrigin=$d4
cCount=$d6
cKernel=$d8
cStart=$da
cSize=$dc

.macro emit3 operand, opcode
  lda #opcode
  sta [cOut]
  lda operand
  ldy #1
  sta [cOut],y
  lda cOut
  clc
  adc #3
  sta cOut
.endmacro

sa1_bullet_cache_init:
  rep #$30
  lda #0
  ldx #0
cache_clear_entries:
  sta f:$430400,x
  inx
  inx
  cpx #512
  bcc cache_clear_entries
  inc
  asl
  asl
  asl
  sta f:$430700
  sta f:$430708
  lda #0
  sta f:$430704
  ldx #2
cache_clear_generations:
  sta f:$430708,x
  inx
  inx
  cpx #16
  bcc cache_clear_generations
  lda #$4000
  sta f:$430702
  rtl

sa1_bullet_cache_prepare:
  rep #$30
  lda $3e
  cmp #6
  bcc cache_other_asset
  cmp #9
  bcc cache_bullet_asset
  cmp #37
  beq cache_bullet_asset
cache_other_asset:
  clc
  rtl
cache_bullet_asset:
  lda $36
  xba
  ora $34
  sta cWH
  lda $38
  and #1
  xba
  .repeat 7
    asl
  .endrepeat
  sta cAF
  lda $3c
  and #$33
  xba
  ora $3e
  ora cAF
  sta cAF
  eor cWH
  sta cSize
  xba
  lsr
  lsr
  eor cSize
  and #63
  asl
  asl
  asl
  sta cMeta
  tax
  lda f:$430400,x
  cmp cWH
  bne cache_miss
  lda f:$430402,x
  cmp cAF
  bne cache_miss
  lda f:$430404,x
  sta cKernel
  and #7
  asl
  tax
  lda f:$430708,x
  cmp cKernel
  bne cache_miss
  ldx cMeta
  lda f:$430406,x
  sta $24
  lda cKernel
  and #7
  tax
  lda f:cache_banks,x
  and #255
  sta $26
  jmp cache_ready
cache_miss:
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
  ; 圧縮行の長さから、この絵のコード量を先に求める。
  lda cV
  sta cRead
  stz cDy
  lda #1
  sta cSize
cache_measure:
  lda cRead
  xba
  and #255
  sta cOffset
  asl
  clc
  adc cOffset
  tay
  lda [cRows],y
  sta cRecord
  iny
  iny
  sep #$20
  lda [cRows],y
  sta cRecord+2
  rep #$20
  lda [cRecord]
  and #255
  clc
  adc #13
  adc cSize
  sta cSize
  lda cRead
  clc
  adc cStep
  sta cRead
  inc cDy
  lda cDy
  cmp $36
  bne cache_measure
  lda cSize
  clc
  adc f:$430702
  bcs cache_next_block
  sta cOffset
  lda f:$430704
  asl
  tax
  lda f:cache_limits,x
  cmp cOffset
  bcs cache_space_ready
cache_next_block:
  lda f:$430704
  inc
  and #7
  sta f:$430704
  bne :+
  lda f:$430700
  clc
  adc #8
  bne cache_round_ready
  ; タグの周回時には以前の世代との一致を防ぐ。
  ldx #0
cache_reset_tags:
  sta f:$430404,x
  txa
  clc
  adc #8
  tax
  lda #0
  cpx #512
  bcc cache_reset_tags
  lda #8
cache_round_ready:
  sta f:$430700
:
  lda f:$430704
  asl
  tax
  lda f:$430704
  ora f:$430700
  sta f:$430708,x
  lda f:cache_starts,x
  sta f:$430702
cache_space_ready:
  lda f:$430702
  sta cStart
  sta cProgram
  lda f:$430704
  tax
  lda f:cache_banks,x
  and #255
  sta cProgram+2
  sta cOut+2
  lda $36
  asl
  sta cSize
  asl
  asl
  clc
  adc cSize
  adc $36
  adc cStart
  inc
  sta cOut
  stz cDy
  jsl sa1_dma_try_begin
  bcc cache_copy_cpu
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
  jml cache_build_row
cache_copy_cpu:
  phb
  ldx #.loword(__BULLETJIT_LOAD__)
  ldy #$0300
  lda #__BULLETJIT_SIZE__-1
  mvn #$01,#$00
  plb
  jml cache_build_row
.segment "BULLETJIT"
cache_build_row:
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
  lda [cRecord]
  sta [cOut]
  lda cOut
  inc
  inc
  sta cOut
  sta cKernel
  ldy #2
  lda [cRecord],y
  and #255
  sta cOrigin
  iny
  lda [cRecord],y
  and #255
  sta cCount
  lda #$00a9
  sta [cProgram]
  lda cDy
  .repeat 7
    asl
  .endrepeat
  clc
  adc cOrigin
  ldy #1
  sta [cProgram],y
  lda #$6518
  ldy #3
  sta [cProgram],y
  lda #$aaf8
  ldy #5
  sta [cProgram],y
  lda #$0022
  ldy #7
  sta [cProgram],y
  lda cKernel
  iny
  sta [cProgram],y
  lda cOut+2
  and #255
  ldy #10
  sta [cProgram],y
  lda cProgram
  clc
  adc #11
  sta cProgram
  lda #4
  sta cRead
  stz cOffset
cache_build_word:
  lda cCount
  jeq cache_finish_row
  ldy cRead
  lda [cRecord],y
  sta cValue
  iny
  iny
  sty cRead
  lda cValue
  jeq cache_next_word
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
  lda cMask
  beq cache_opaque_word
  emit3 cOffset,$bd
  emit3 cMask,$29
  emit3 cValue,$09
  bra cache_store_word
cache_opaque_word:
  emit3 cValue,$a9
cache_store_word:
  emit3 cOffset,$9d
cache_next_word:
  inc cOffset
  inc cOffset
  dec cCount
  jmp cache_build_word
cache_finish_row:
  lda #$006b
  sta [cOut]
  inc cOut
  lda cV
  clc
  adc cStep
  sta cV
  inc cDy
  lda cDy
  cmp $36
  jne cache_build_row
  sep #$20
  lda #$6b
  sta [cProgram]
  rep #$20
  lda cOut
  sta f:$430702
  ldx cMeta
  lda cWH
  sta f:$430400,x
  lda cAF
  sta f:$430402,x
  lda f:$430704
  asl
  tax
  lda f:$430708,x
  ldx cMeta
  sta f:$430404,x
  lda cStart
  sta f:$430406,x
  sta $24
  lda cProgram+2
  and #255
  sta $26
  jml cache_ready
.segment "GSU"
cache_ready:
  lda $3c
  bit #$30
  beq :+
  stz $c0
  lda $36
  xba
  ora $34
  sta $c2
:
  sec
  rtl
cache_dimensions:
.incbin "flip_dimensions.bin"
cache_banks:
.byte $43,$40,$40,$41,$41,$42,$42,$43
cache_starts:
.word $4000,$6400,$e400,$6400,$e400,$6400,$e400,$e400
cache_limits:
.word $7fff,$7fff,$ffff,$7fff,$ffff,$7fff,$ffff,$ffff
cache_masks:
.repeat 256, I
  .byte ((I & 15)=0)*15 | ((I & 240)=0)*240
.endrepeat
