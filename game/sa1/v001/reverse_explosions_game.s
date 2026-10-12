; 対象寸法のnative行を右wordから生成し、隠れた命令を飛ばして直接描く。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_reverse_explosions: far, reverse_row_invoke: far
.import __REVJIT_LOAD__, __REVJIT_SIZE__
.import sa1_dma_try_begin: far, sa1_dma_end: far
.ifdef SA1_REVERSE_HINT_COMPRESSED
.import hint_delta_sums: far, hint_delta_masks: far
.endif
rRows=$a0
rFirst=$a4
rLast=$a6
rCode=$a8
rHint=$ac
rOrigin=$b0
rTemp=$b2
rDest=$b4
rLimit=$b6
rGuard=$b8
rGuardOffset=$ba
rRawX=$bc
rRowBase=$be
rCount=$c0
rHeader=$c2
rChain=$c6
rNativeOffset=$ca
.segment "GSU"
sa1_reverse_explosions:
  rep #$30
  lda $38
  jmi reverse_no
  cmp #256
  jcs reverse_no
  lda $3a
  bpl :+
  clc
  adc $36
  jmi reverse_no
  jeq reverse_no
  bra :++
:
  cmp #192
  jcs reverse_no
:
  lda $3c
  and #$33
  jne reverse_no
.ifdef SA1_REVERSE_RECORD_NATIVE
  lda $24
  sta rChain
  lda $26
  and #255
  sta rChain+2
.endif
.ifdef SA1_REVERSE_INLINE_HINTS
  lda $24
  sta rRows
  lda $26
  and #255
  sta rRows+2
.else
  lda $2c
  asl
  tax
  lda f:$433000,x
  sta rTemp
  lda f:$df6fe0
  asl
  asl
  asl
  sta rCount
  ldx #0
reverse_find:
  txa
  cmp rCount
  jcs reverse_no
  lda f:$df6fe2,x
  cmp rTemp
  beq reverse_found
  txa
  clc
  adc #8
  tax
  bra reverse_find
reverse_found:
  lda $38
  and #1
  beq :+
  inx
  inx
  inx
:
  lda f:$df6fe4,x
  sta rRows
  sep #$20
  lda f:$df6fe6,x
  sta rRows+2
  rep #$20
.endif
  jsl sa1_dma_try_begin
  bcc reverse_load_cpu
  lda #__REVJIT_SIZE__
  sta $2238
  lda #.loword(__REVJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__REVJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  jml reverse_entry
reverse_load_cpu:
  phb
  lda #__REVJIT_SIZE__-1
  ldx #.loword(__REVJIT_LOAD__)
  ldy #$0300
  mvn #^__REVJIT_LOAD__,#$00
  plb
  jml reverse_entry
reverse_no:
  clc
  rtl
.segment "REVJIT"
reverse_entry:
  rep #$30
  phb
  stz rFirst
  lda $3a
  bpl :+
  eor #$ffff
  inc
  sta rFirst
:
  lda #192
  sec
  sbc $3a
  cmp $36
  bcc :+
  lda $36
:
  sec
  sbc rFirst
  sta rLast
  lda rFirst
  asl
  asl
  asl
.ifdef SA1_REVERSE_RECORD_COMPACT
  sec
  sbc rFirst
  sbc rFirst
.endif
.ifdef SA1_REVERSE_RECORD_NATIVE
  clc
  adc rFirst
  adc rFirst
  adc rFirst
  clc
  adc rChain
  sta rChain
  lda rFirst
  .repeat 7
    asl
  .endrepeat
  sta rNativeOffset
  lda rFirst
  asl
  clc
  adc rFirst
.endif
.ifdef SA1_REVERSE_INLINE_HINTS
  clc
  adc rFirst
  adc rFirst
  adc rFirst
.endif
  clc
  adc rRows
  sta rRows
  lda rFirst
  clc
  adc $3a
  .repeat 7
    asl
  .endrepeat
  clc
  adc f:$00019a
  sta rRowBase
  clc
  adc #128
  sta rGuardOffset
  lda $38
  lsr
  sta rRawX
  clc
  adc rRowBase
  sta rRowBase
  lda #128
  sec
  sbc rRawX
  sta rLimit
  sep #$20
  lda #$5c
  sta f:$000700
  lda f:$000102
  pha
  plb
  rep #$20
reverse_row:
.ifdef SA1_REVERSE_INLINE_HINTS
  ldy #8
  lda [rRows],y
  sta rCode
  sec
  sbc #5
  sta rHeader
  iny
  iny
  lda [rRows],y
  and #255
  sta rCode+2
  sta rHeader+2
  ldy #3
  lda [rHeader],y
  and #$ff00
  sta rOrigin
  ldy #1
  lda [rRows],y
  and #127
  ora rOrigin
  sta rOrigin
  ldy #0
  lda [rHeader],y
  sta rHint
  iny
  iny
  lda [rHeader],y
  and #255
  sta rHint+2
  lda rOrigin
.else
.ifdef SA1_REVERSE_RECORD_NATIVE
  ldy #1
  lda [rChain],y
  sec
  sbc rNativeOffset
  sta rOrigin
  ldy #8
  lda [rChain],y
  sta rCode
  sec
  sbc #1
  sta rHeader
  ldy #10
  lda [rChain],y
  and #255
  sta rCode+2
  sta rHeader+2
  lda [rHeader]
  and #255
  xba
  ora rOrigin
  sta rOrigin
  ldy #0
  lda [rRows],y
  sta rHint
  iny
  iny
  lda [rRows],y
  and #255
  sta rHint+2
  lda rOrigin
.else
.ifdef SA1_REVERSE_RECORD_COMPACT
  ldy #0
  lda [rRows],y
  sta rCode
  iny
  iny
  lda [rRows],y
  sta rHint
  iny
  iny
  lda [rRows],y
  sta rHeader
  and #31
  asl
  sta rOrigin
  lda rHeader
  and #$07e0
  .repeat 4
    lsr
  .endrepeat
  xba
  ora rOrigin
  sta rOrigin
  lda rHeader
  xba
  lsr
  lsr
  lsr
  and #15
  tax
  lda f:$df71f0,x
  and #255
  sta rCode+2
  lda rHeader
  bpl reverse_hint_bank_df
  lda #$fe
  bra reverse_hint_bank_ready
reverse_hint_bank_df:
  lda #$df
reverse_hint_bank_ready:
  sta rHint+2
  lda rOrigin
.else
  ldy #0
  lda [rRows],y
  sta rCode
  iny
  iny
  lda [rRows],y
  sta rCode+2
  iny
  lda [rRows],y
  sta rHint
  iny
  iny
  lda [rRows],y
  sta rHint+2
  iny
  lda [rRows],y
  sta rOrigin
.endif
.endif
.endif
  and #255
  cmp rLimit
  jcs reverse_advance
  lda rLimit
  sec
  sbc rOrigin
  and #255
  sta rTemp
  lda rOrigin+1
  and #255
  jeq reverse_advance
  cmp rTemp
.ifdef SA1_REVERSE_FULL_ROW_FAST
  jcc reverse_full_row
  jeq reverse_full_row
  lda rTemp
.else
  bcc :+
  lda rTemp
:
.endif
  inc
  lsr
  tay
.ifdef SA1_REVERSE_HINT_COMPRESSED
  lda [rHint]
  and #128
  jeq reverse_hint_raw
  tya
  and #7
  sta rRawX
  tya
  lsr
  lsr
  lsr
  sta rTemp
  asl
  clc
  adc rTemp
  inc
  tay
  lda [rHint],y
  and #255
  sta rTemp
  iny
  lda [rHint],y
  sta rHeader
  lda rRawX
  cmp #4
  bcc reverse_hint_tail
  lda rHeader
  and #255
  tax
  lda f:hint_delta_sums,x
  and #255
  sta rDest
  lda rTemp
  sec
  sbc rDest
  sta rTemp
  lda rHeader
  xba
  sta rHeader
  lda rRawX
  sec
  sbc #4
reverse_hint_tail:
  asl
  tax
  lda f:hint_delta_masks,x
  and rHeader
  tax
  lda f:hint_delta_sums,x
  and #255
  sta rDest
  lda rTemp
  sec
  sbc rDest
  bra reverse_hint_decoded
reverse_hint_raw:
  lda [rHint],y
  and #255
reverse_hint_decoded:
  sta rTemp
  asl
  clc
  adc rTemp
.else
  lda [rHint],y
  and #255
.endif
  clc
  adc rCode
.ifdef SA1_REVERSE_FULL_ROW_FAST
  bra reverse_entry_ready
reverse_full_row:
  lda rCode
reverse_entry_ready:
.endif
  sta f:$000701
  sep #$20
  lda rCode+2
  sta f:$000703
  rep #$20
  lda rOrigin
  and #255
  clc
  adc rRowBase
  sta rDest
  ldx rGuardOffset
  sep #$20
  lda a:$0000,x
  sta rGuard
  rep #$20
  ldx rDest
reverse_row_invoke:
  jsl $000700
  ldx rGuardOffset
  sep #$20
  lda rGuard
  sta a:$0000,x
  rep #$20
reverse_advance:
  lda rRows
  clc
.ifdef SA1_REVERSE_INLINE_HINTS
  adc #11
.else
.ifdef SA1_REVERSE_RECORD_NATIVE
  adc #3
.else
.ifdef SA1_REVERSE_RECORD_COMPACT
  adc #6
.else
  adc #8
.endif
.endif
.endif
  sta rRows
.ifdef SA1_REVERSE_RECORD_NATIVE
  lda rChain
  clc
  adc #11
  sta rChain
  lda rNativeOffset
  clc
  adc #128
  sta rNativeOffset
.endif
  lda rRowBase
  clc
  adc #128
  sta rRowBase
  lda rGuardOffset
  clc
  adc #128
  sta rGuardOffset
  dec rLast
  jne reverse_row
  plb
  sec
  rtl
