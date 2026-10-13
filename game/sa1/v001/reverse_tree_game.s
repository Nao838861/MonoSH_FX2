; 木4は右から生成した行の可視suffixへ直接入る。左端/画面内は既存chunkを使用。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_reverse_tree_right: far, tree_right_row: far, tree_right_invoke: far
.segment "GSU"
tChain=$80
tCode=$84
tDest=$88
tLimit=$8a
tHeader=$8c
tHint=$90
tTemp=$94
tCount=$96
tGuard=$98
tGuardByte=$9a
sa1_reverse_tree_right:
  rep #$30
  phb
  lda $a2
  sec
  sbc $a0
  sta tCount
  lda $a0
  asl
  sta tTemp
  asl
  asl
  clc
  adc tTemp
  adc $a0
  clc
  adc $24
  sta tChain
  lda $26
  and #255
  sta tChain+2
  sep #$20
  lda #$5c
  sta f:$000700
  lda f:$000102
  pha
  plb
  rep #$20
tree_right_row:
  ldy #1
  lda [tChain],y
  clc
  adc $f8
  sta tDest
  lda [tChain],y
  and #127
  clc
  adc $48
  sta tTemp
  lda #128
  sec
  sbc tTemp
  jmi tree_right_next
  jeq tree_right_next
  sta tLimit
  ldy #8
  lda [tChain],y
  sta tCode
  sec
  sbc #3
  sta tHeader
  ldy #10
  lda [tChain],y
  and #255
  sta tCode+2
  sta tHeader+2
  ldy #2
  lda [tHeader],y
  and #255
  jeq tree_right_next
  cmp tLimit
  bcc tree_right_full
  beq tree_right_full
  lda [tHeader]
  and #255
  sta tTemp
  asl
  clc
  adc tTemp
  tax
  lda f:$df6fe0,x
  sta tHint
  lda f:$df6fe2,x
  and #255
  sta tHint+2
  lda tLimit
  inc
  lsr
  tay
  lda [tHint],y
  and #255
  clc
  adc tCode
  bra tree_right_ready
tree_right_full:
  lda tCode
tree_right_ready:
  sta f:$000701
  sep #$20
  lda tCode+2
  sta f:$000703
  rep #$20
  lda tDest
  clc
  adc tLimit
  sta tGuard
  tax
  sep #$20
  lda a:$0000,x
  sta tGuardByte
  rep #$20
  ldx tDest
tree_right_invoke:
  jsl $000700
  ldx tGuard
  sep #$20
  lda tGuardByte
  sta a:$0000,x
  rep #$30
tree_right_next:
  lda tChain
  clc
  adc #11
  sta tChain
  dec tCount
  jne tree_right_row
  plb
  sec
  rtl
