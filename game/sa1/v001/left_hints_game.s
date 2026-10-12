.setcpu "65816"
.smart
.macpack longbranch
.include "left_hints.inc"
.export sa1_left_hint_draw: far
.import __LEFTJIT_LOAD__, __LEFTJIT_SIZE__
.import sa1_dma_try_begin: far, sa1_dma_end: far
.segment "GSU"
sa1_left_hint_draw:
  rep #$30
.ifdef SA1_CLIP_RESIDENT
.export clip_left_cache_hit: far, clip_left_cache_miss: far
  lda $07fc
  cmp #1
  bne :+
clip_left_cache_hit:
  jml left_hint_entry
:
clip_left_cache_miss:
.endif
  jsl sa1_dma_try_begin
  bcc hint_load_cpu
  lda #__LEFTJIT_SIZE__
  sta $2238
  lda #.loword(__LEFTJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__LEFTJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
.ifdef SA1_CLIP_RESIDENT
  bra hint_loaded
.else
  jml left_hint_entry
.endif
hint_load_cpu:
  phb
  lda #__LEFTJIT_SIZE__-1
  ldx #.loword(__LEFTJIT_LOAD__)
  ldy #$0300
  mvn #^__LEFTJIT_LOAD__,#$00
  plb
hint_loaded:
.ifdef SA1_CLIP_RESIDENT
  lda #1
  sta $07fc
.endif
  jml left_hint_entry
.ifdef SA1_LEFT_HINT_COMPRESSED
.export hint_delta_sums: far, hint_delta_masks: far
; 2bit差分4個の和。最後のgroupはmaskで不要な差分を0にする。
hint_delta_sums:
  .repeat 256, n
    .byte ((n&3)+((n>>2)&3)+((n>>4)&3)+((n>>6)&3)) + ((n&3)=3) + (((n>>2)&3)=3) + (((n>>4)&3)=3) + (((n>>6)&3)=3)
  .endrepeat
hint_delta_masks:
  .word 0,3,15,63
.endif
.segment "LEFTJIT"
hintChain=$80
hintCode=$84
hintTable=$88
hintCur=$90
hintDest=$92
hintGuard=$94
hintByte=$96
hintA=$98
hintSlot=$9a
hintPrevious=$b6
hintPreviousBank=$b8
hintPreviousCur=$ba
hintPreviousEntry=$bc
hintPreviousA=$be
left_hint_entry:
  rep #$30
  phb
  sep #$20
  lda f:$000102
  pha
  plb
  rep #$20
  lda #$ffff
  sta hintPrevious
  lda $a0                       ; first visible row
  asl
  sta hintSlot
  asl
  asl
  clc
  adc hintSlot
  adc $a0
  clc
  adc $24
  sta hintChain
  lda $26
  sta hintChain+2
hint_row:
  ldy #1
  lda [hintChain],y
  clc
  adc $f8
  sta hintDest
  ldy #1
  lda [hintChain],y
  and #127
  clc
  adc $48                       ; signed horizontal byte origin
  sta hintCur
  ldy #8
  lda [hintChain],y
  sta hintCode
  iny
  iny
  sep #$20
  lda [hintChain],y
  sta hintCode+2
  sta f:$0007f3
  rep #$20
  lda hintCode+2
  and #255
  sta hintCode+2
  lda hintCode
  cmp hintPrevious
  bne hint_new_code
  lda hintCode+2
  cmp hintPreviousBank
  bne hint_new_code
  lda hintCur
  cmp hintPreviousCur
  bne hint_new_code
  lda hintPreviousEntry
  sta f:$0007f1
  lda hintPreviousA
  sta hintA
  jmp hint_invoke
hint_new_code:
  stz hintA
  lda hintCode
  sta f:$0007f1
  lda hintCur
  jpl hint_remember
  lda hintCode
  dec
  sta hintTable
  lda hintCode+2
  sta hintTable+2
  lda [hintTable]
  and #255
  clc
  adc hintCur
  jmi hint_advance
  jeq hint_advance
.ifdef SA1_FLAME_DIRECT_HINTS
  lda $3e
  cmp #31
  bne hint_flame_regular
.export flame_direct_row: far
flame_direct_row:
  lda hintCode
  sec
  sbc #5
  sta hintTable
  ldy #2
  lda [hintTable],y
  and #255
  pha
  lda [hintTable]
  sta hintTable
  pla
  sta hintTable+2
  lda hintCur
  eor #$ffff
  inc
  lsr
  sta hintSlot
  asl
  clc
  adc hintSlot
  tay
  lda [hintTable],y
  and #255
  clc
  adc hintCode
  sta f:$0007f1
  iny
  lda [hintTable],y
  sta hintA
  jmp hint_remember
hint_flame_regular:
.endif
.ifdef SA1_LEFT_HINT_INLINE
  lda hintCode
  sec
  sbc #5
  sta hintTable
  ldy #2
  lda [hintTable],y
  and #255
  pha
  lda [hintTable]
  sta hintTable
  pla
  sta hintTable+2
  jmp hint_decode
.else
  lda hintCode
  lsr
  sta hintSlot
  lda hintCode+2
  and #255
  asl
  asl
  asl
  eor hintSlot
  and #LEFT_HINT_MASK
hint_hash:
  sta hintSlot
  asl
  sta hintTable
  asl
  clc
  adc hintTable
  tax
  lda f:LEFT_HINT_TABLE,x
.ifdef SA1_LEFT_RUNTIME_SCAN
  jeq hint_scan
.endif
  cmp hintCode
  bne hint_next_hash
  lda f:LEFT_HINT_TABLE+2,x
  and #255
  cmp hintCode+2
  beq hint_found
hint_next_hash:
  lda hintSlot
  inc
  and #LEFT_HINT_MASK
  bra hint_hash
.ifdef SA1_LEFT_RUNTIME_SCAN
; 事前hintのない行も、左に隠れたwordだけを読み飛ばしてROMから直接描く。
; 同じコード・左位置が続く行は、既存の直前行cacheをそのまま使う。
hint_scan:
  stz hintSlot
  ldy #0
hint_scan_op:
  lda [hintCode],y
  and #255
  cmp #$6b
  beq hint_scan_empty
  cmp #$a9
  bne hint_scan_store
  iny
  lda [hintCode],y
  sta hintA
  dey
  bra hint_scan_next
hint_scan_store:
  cmp #$9d
  bne hint_scan_next
  iny
  lda [hintCode],y
  dey
  clc
  adc hintCur
  inc
  bpl hint_scan_found
  tya
  clc
  adc #3
  sta hintSlot
hint_scan_next:
  iny
  iny
  iny
  bra hint_scan_op
hint_scan_empty:
  sty hintSlot
hint_scan_found:
  lda hintSlot
  clc
  adc hintCode
  sta f:$0007f1
  jmp hint_remember
.endif
hint_found:
  lda f:LEFT_HINT_TABLE+3,x
  sta hintTable
  sep #$20
  lda f:LEFT_HINT_TABLE+5,x
  sta hintTable+2
  rep #$20
.endif
hint_decode:
  lda hintCur
  eor #$ffff
  inc
  lsr
  tay
.ifdef SA1_LEFT_DIRECT
  tya
  asl
  tay
.export direct_left_row: far
direct_left_row:
  lda [hintTable],y
  sta hintSlot
  and #255
  clc
  adc hintCode
  sta f:$0007f1
  lda hintSlot
  xba
  and #255
  asl
  tax
  lda f:LEFT_INITIAL_TABLE,x
  sta hintA
  jmp hint_remember
.else
.ifdef SA1_LEFT_HINT_COMPRESSED
  lda [hintTable]
  and #128
  beq hint_uncompressed
  tya
  and #7
  sta hintGuard
  tya
  lsr
  lsr
  lsr
  sta hintSlot
  asl
  clc
  adc hintSlot
  inc
  tay
  lda [hintTable],y
  and #255
  sta hintSlot
  iny
  lda [hintTable],y
  sta hintByte
  lda hintGuard
  cmp #4
  bcc hint_delta_tail
  lda hintByte
  and #255
  tax
  lda f:hint_delta_sums,x
  and #255
  clc
  adc hintSlot
  sta hintSlot
  lda hintByte
  xba
  sta hintByte
  lda hintGuard
  sec
  sbc #4
hint_delta_tail:
  asl
  tax
  lda f:hint_delta_masks,x
  and hintByte
  tax
  lda f:hint_delta_sums,x
  and #255
  clc
  adc hintSlot
  bra hint_decoded
hint_uncompressed:
.endif
  lda [hintTable],y
  and #255
.ifdef SA1_LEFT_HINT_COMPRESSED
hint_decoded:
.endif
  sta hintSlot
  asl
  clc
  adc hintSlot
  sta hintSlot
  clc
  adc hintCode
  sta f:$0007f1
  ldy hintSlot
  lda [hintCode],y
  and #255
  cmp #$9d
  bne hint_remember
.ifdef SA1_LEFT_BYTE_CONSTANT_SCAN
  sep #$20
.endif
hint_find_constant:
  dey
  dey
  dey
  lda [hintCode],y
.ifndef SA1_LEFT_BYTE_CONSTANT_SCAN
  and #255
.endif
  cmp #$a9
  bne hint_find_constant
  iny
.ifdef SA1_LEFT_BYTE_CONSTANT_SCAN
  rep #$20
.endif
  lda [hintCode],y
  sta hintA
.endif
hint_remember:
  lda hintCode
  sta hintPrevious
  lda hintCode+2
  sta hintPreviousBank
  lda hintCur
  sta hintPreviousCur
  lda f:$0007f1
  sta hintPreviousEntry
  lda hintA
  sta hintPreviousA
hint_invoke:
  lda hintDest
  sec
  sbc hintCur
  dec
  sta hintGuard
  sep #$20
  ldx hintGuard
  lda a:$0000,x
  sta hintByte
  rep #$20
  ldx hintDest
  lda hintA
  jsr $07f0
  ldx hintGuard
  sep #$20
  lda hintByte
  sta a:$0000,x
  rep #$30
hint_advance:
  lda hintChain
  clc
  adc #11
  sta hintChain
  inc $a0
  lda $a0
  cmp $a2
  jcc hint_row
.export left_hint_finished: far
left_hint_finished:
  plb
  sec
  rtl
