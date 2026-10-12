; 手前の不透明区間に隠れるnative先頭を省く。行chainのJSL先だけ更新する。
.setcpu "65816"
.smart
.macpack longbranch
.include "opaque_prefix.inc"
.export sa1_opaque_prefix: far, opaque_prefix_selected: far, opaque_prefix_patched: far
.export opaque_prefix_patch_done: far
.export opaque_prefix_finished: far
.import __OPJIT_LOAD__, __OPJIT_SIZE__
.import sa1_dma_try_begin: far, sa1_dma_end: far
.import hint_delta_sums: far, hint_delta_masks: far
sScan=$80
sIndex=$84
sArea=$86
sLeft=$88
sTop=$8a
sWidth=$8c
sHeight=$8e
sAsset=$90
sRight=$92
sBottom=$94
sDX=$96
sDY=$98
sTemp=$9a
sBackRight=$a0
sBackBottom=$a2
frontLeft=$b0
frontTop=$b2
frontHeight=$b4
frontWidth=$b6
frontAsset=$b8
frontSpans=$ba
.segment "GSU"
sa1_opaque_prefix:
.ifdef SA1_OPAQUE_BYPASS
  clc
  rtl
  nop
.else
  brl prefix_select_start
.endif
prefix_select_start:
  rep #$30
  stz sArea
  lda $38
  clc
  adc $34
  sta sBackRight
  lda $3a
  clc
  adc $36
  sta sBackBottom
  lda $28
  clc
  adc #10
  sta sScan
  lda $2a
  and #255
  sta sScan+2
  lda $2c
  inc
  sta sIndex
  sep #$20
  stz $2250
  rep #$20
select_next_object:
  lda sIndex
  cmp $2e
  jcs select_done
  ldy #7
  lda [sScan],y
  and #255
  jne select_advance
  ldy #6
  lda [sScan],y
  and #255
  cmp #39
  jcc select_advance
  cmp #42
  jcs select_advance
  sta sAsset
  ldy #4
  lda [sScan],y
  and #255
  cmp #64
  jcc select_advance
  cmp #129
  jcs select_advance
  sta sWidth
  lsr
  sta sTemp
  lda [sScan]
  sec
  sbc sTemp
  sta sLeft
  clc
  adc sWidth
  sta sRight
  ldy #5
  lda [sScan],y
  and #255
  sta sHeight
  ldy #2
  lda [sScan],y
  sec
  sbc #20
  sta sBottom
  sec
  sbc sHeight
  sta sTop
  lda sLeft
  sec
  sbc $38
  bpl :+
  lda $38
  bra :++
:
  lda sLeft
:
  sta sTemp
  lda sRight
  sec
  sbc sBackRight
  bmi :+
  lda sBackRight
  bra :++
:
  lda sRight
:
  sec
  sbc sTemp
  jmi select_advance
  jeq select_advance
  sta sDX
  lda sTop
  sec
  sbc $3a
  bpl :+
  lda $3a
  bra :++
:
  lda sTop
:
  sta sTemp
  lda sBottom
  sec
  sbc sBackBottom
  bmi :+
  lda sBackBottom
  bra :++
:
  lda sBottom
:
  sec
  sbc sTemp
  bmi select_advance
  beq select_advance
  sta sDY
  lda sDX
  sta $2251
  lda sDY
  sta $2253
  nop
  nop
  lda $2306
  cmp sArea
  bcc select_advance
  beq select_advance
  sta sArea
  lda sLeft
  sta frontLeft
  lda sTop
  sta frontTop
  lda sHeight
  sta frontHeight
  lda sWidth
  sta frontWidth
  lda sAsset
  sta frontAsset
select_advance:
  lda sScan
  clc
  adc #10
  sta sScan
  inc sIndex
  jmp select_next_object
select_done:
  lda sArea
  jeq prefix_decline
  lda frontAsset
  sec
  sbc #39
  asl
  sta sTemp
  .repeat 6
    asl
  .endrepeat
  clc
  adc sTemp
  sta sTemp
  lda frontWidth
  sec
  sbc #64
  asl
  clc
  adc sTemp
  tax
  lda f:OPAQUE_SPAN_TABLE,x
  jeq prefix_decline
  tax
  lda f:$ff0000,x
  and #255
  sta sIndex
  inx
select_height:
  lda f:$ff0000,x
  and #255
  cmp frontHeight
  beq select_height_found
  txa
  clc
  adc #3
  tax
  dec sIndex
  bne select_height
prefix_decline:
  clc
  rtl
select_height_found:
  lda f:$ff0001,x
  sta frontSpans
opaque_prefix_selected:
  stz $019c                    ; 0300..06ffのbullet workerを上書きする。
  jsl sa1_dma_try_begin
  bcc prefix_load_cpu
  lda #__OPJIT_SIZE__
  sta $2238
  lda #.loword(__OPJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__OPJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  jml prefix_entry
prefix_load_cpu:
  phb
  lda #__OPJIT_SIZE__-1
  ldx #.loword(__OPJIT_LOAD__)
  ldy #$0300
  mvn #^__OPJIT_LOAD__,#$00
  plb
  jml prefix_entry
opaque_nibble_sums:
.ifndef SA1_OPAQUE_INLINE_RAW
  .repeat 256, n
    .byte (n&15)+(n>>4)
  .endrepeat
.endif

wChain=$80
wRow=$84
wRemaining=$86
wChunk=$88
wBytes=$8a
wSlot=$8c
wCurrentRow=$8e
wCode=$92
wHeader=$96
wHint=$9a
wPacked=$9e
wBase=$a0
wWordIndex=$a2
wTemp=$a4
wRank=$a6
wBits=$a8
wUnit=$aa
.segment "OPJIT"
prefix_entry:
  rep #$30
  stz wRow
  lda $3a
  bpl :+
  eor #$ffff
  inc
  sta wRow
:
  lda #192
  sec
  sbc $3a
  cmp $36
  bcc :+
  lda $36
:
  sec
  sbc wRow
  jmi prefix_finished
  jeq prefix_finished
  sta wRemaining
  lda $3a
  .repeat 7
    asl
  .endrepeat
  clc
  adc $48
  clc
  adc f:$00019a
  sta $f8
  lda wRow
  asl
  sta wTemp
  asl
  asl
  clc
  adc wTemp
  adc wRow
  clc
  adc $24
  sta wChain
  lda $26
  and #255
  sta wChain+2
prefix_chunk:
  lda wRemaining
  cmp #21
  bcc :+
  lda #20
:
  sta wChunk
  asl
  sta wTemp
  asl
  asl
  clc
  adc wTemp
  adc wChunk
  sta wBytes
  jsl sa1_dma_try_begin
  bcc prefix_chain_cpu
  lda wBytes
  sta $2238
  lda wChain
  sta $2232
  sep #$20
  lda wChain+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0700
  sta $2235
  jsl sa1_dma_end
  bra prefix_chain_ready
prefix_chain_cpu:
  sep #$20
  lda #$54
  sta f:$0007ec
  lda #0
  sta f:$0007ed
  lda wChain+2
  sta f:$0007ee
  lda #$6b
  sta f:$0007ef
  rep #$30
  ldx wChain
  ldy #$0700
  lda wBytes
  dec
  jsl $0007ec
prefix_chain_ready:
  ldx wBytes
  sep #$20
  lda #$6b
  sta f:$000700,x
  rep #$20
  stz wSlot
  lda wRow
  sta wCurrentRow
prefix_patch_row:
  lda wCurrentRow
  clc
  adc $3a
  sec
  sbc frontTop
  jmi prefix_next_row
  cmp frontHeight
  jcs prefix_next_row
  asl
  clc
  adc frontSpans
  tax
  lda f:$ff0000,x
  sta wPacked
  and #255
  clc
  adc frontLeft
  sta wTemp
  ldx wSlot
  lda f:$000701,x
  and #127
  asl
  sta wBase
  lda $38
  and #$fffe
  clc
  adc wBase
  sta wBase
  sec
  sbc wTemp
  jmi prefix_next_row
  lda wPacked
  xba
  and #255
  clc
  adc frontLeft
  sec
  sbc wBase
  cmp #4
  jmi prefix_next_row
  jcc prefix_next_row
  lsr
  lsr
  sta wWordIndex
  lda f:$000708,x
  sta wCode
  sec
.ifdef SA1_OPAQUE_INLINE_RAW
  sbc #2
.else
  sbc #5
.endif
  sta wHeader
  lda f:$00070a,x
  and #255
  sta wCode+2
  sta wHeader+2
.ifdef SA1_OPAQUE_INLINE_RAW
  ldy #1
.else
  ldy #4
.endif
  lda [wHeader],y
  and #255
  lsr
  cmp wWordIndex
  bcc prefix_hide_all
  beq prefix_hide_all
.ifdef SA1_OPAQUE_INLINE_RAW
  inc                         ; rawの個数はextent/2+1。headerの直前に置く。
  sta wTemp
  lda wHeader
  sec
  sbc wTemp
  sta wHint
  lda wCode+2
  sta wHint+2
  ldy wWordIndex
  lda [wHint],y
  and #255
  bra prefix_decoded
.else
  ldy #2
  lda [wHeader],y
  and #255
  sta wHint+2
  lda [wHeader]
  sta wHint
  lda [wHint]
  and #255
  cmp #128
  beq prefix_decode_two
  cmp #129
  jeq prefix_decode_nibble
  ldy wWordIndex
  lda [wHint],y
  and #255
  jmp prefix_decoded
.endif
prefix_hide_all:
.ifdef SA1_OPAQUE_INLINE_RAW
  ldy #0
.else
  ldy #3
.endif
  lda [wHeader],y
  and #255
  dec
  clc
  adc wCode
  ldx wSlot
  jmp opaque_prefix_patched
.ifndef SA1_OPAQUE_INLINE_RAW
prefix_decode_two:
  lda wWordIndex
  and #7
  sta wRank
  lda wWordIndex
  lsr
  lsr
  lsr
  sta wTemp
  asl
  clc
  adc wTemp
  inc
  tay
  lda [wHint],y
  and #255
  sta wUnit
  iny
  lda [wHint],y
  sta wBits
  lda wRank
  cmp #4
  bcc prefix_two_tail
  lda wBits
  and #255
  tax
  lda f:hint_delta_sums,x
  and #255
  clc
  adc wUnit
  sta wUnit
  lda wBits
  xba
  sta wBits
  lda wRank
  sec
  sbc #4
prefix_two_tail:
  asl
  tax
  lda f:hint_delta_masks,x
  and wBits
  tax
  lda f:hint_delta_sums,x
  and #255
  clc
  adc wUnit
  bra prefix_decoded
prefix_decode_nibble:
  lda wWordIndex
  and #7
  sta wRank
  lda wWordIndex
  lsr
  lsr
  lsr
  sta wTemp
  asl
  asl
  clc
  adc wTemp
  inc
  tay
  lda [wHint],y
  and #255
  sta wUnit
  iny
prefix_nibble_pair:
  lda wRank
  cmp #2
  bcc prefix_nibble_tail
  sec
  sbc #2
  sta wRank
  lda [wHint],y
  and #255
  tax
  lda f:opaque_nibble_sums,x
  and #255
  clc
  adc wUnit
  sta wUnit
  iny
  bra prefix_nibble_pair
prefix_nibble_tail:
  lda wRank
  beq prefix_nibble_done
  lda [wHint],y
  and #15
  clc
  adc wUnit
  sta wUnit
prefix_nibble_done:
  lda wUnit
.endif
prefix_decoded:
  sta wTemp
  asl
  clc
  adc wTemp
  clc
  adc wCode
  ldx wSlot
opaque_prefix_patched:
  sta f:$000708,x
opaque_prefix_patch_done:
  nop
prefix_next_row:
  inc wCurrentRow
  lda wSlot
  clc
  adc #11
  sta wSlot
  cmp wBytes
  jcc prefix_patch_row
  sep #$20
  lda f:$000102
  pha
  plb
  rep #$20
  jsl $000700
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  lda wChain
  clc
  adc wBytes
  sta wChain
  lda wRow
  clc
  adc wChunk
  sta wRow
  lda wRemaining
  sec
  sbc wChunk
  sta wRemaining
  jne prefix_chunk
prefix_finished:
opaque_prefix_finished:
  sec
  rtl
