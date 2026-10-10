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
  jml left_hint_entry
hint_load_cpu:
  phb
  lda #__LEFTJIT_SIZE__-1
  ldx #.loword(__LEFTJIT_LOAD__)
  ldy #$0300
  mvn #^__LEFTJIT_LOAD__,#$00
  plb
  jml left_hint_entry
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
hint_found:
  lda f:LEFT_HINT_TABLE+3,x
  sta hintTable
  sep #$20
  lda f:LEFT_HINT_TABLE+5,x
  sta hintTable+2
  rep #$20
  lda hintCur
  eor #$ffff
  inc
  lsr
  tay
  lda [hintTable],y
  and #255
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
hint_find_constant:
  dey
  dey
  dey
  lda [hintCode],y
  and #255
  cmp #$a9
  bne hint_find_constant
  iny
  lda [hintCode],y
  sta hintA
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
  plb
  sec
  rtl
