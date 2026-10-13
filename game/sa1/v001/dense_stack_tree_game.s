; 木4の連続wordをPEA/PHAで描く。通常Sへ戻してから割込を許可する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dma_try_begin: far, sa1_dma_end: far
.export sa1_dense_stack_tree: far, dense_tree_row_begin: far, dense_tree_row_done: far
.export dense_tree_copy_dma: far, dense_tree_copy_cpu: far, dense_tree_cache_hit: far
.segment "GSU"
tChain=$80
tCode=$84
tDest=$88
tCur=$8a
tHeader=$8c
tHint=$90
tTemp=$94
tCount=$96
tGuard=$98
tByte=$9a
tLength=$9c
tLastCode=$a0
tLastBank=$a2
tLastCur=$a4
tLastLength=$a6
tSaved=$a8
tEnd=$aa
tJump=$ac
tRawBank=$b0
tMap=$b2
tSP=$b4
tGuardFlag=$b6
sa1_dense_stack_tree:
  rep #$30
  php
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
  stz tChain+2
  sep #$20
  lda $26
  sta tChain+2
  lda #0
  pha
  plb
  rep #$20
  tsc
  sta tSaved
  lda $0102
  and #255
  sta tRawBank
  lda #$ffff
  sta tLastCode
  sta tLastBank
  sta tLastCur
  lda #.loword(dense_tree_row_done)
  sta $0701
  sep #$20
  lda #$5c
  sta $0700
  lda #^dense_tree_row_done
  sta $0703
  rep #$20
tree_row:
  stz tGuardFlag
  ldy #1
  lda [tChain],y
  clc
  adc $f8
  sta tDest
  lda [tChain],y
  and #127
  clc
  adc $48
  sta tCur
  cmp #128
  jpl tree_next
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
  sta tJump+2
  ldy #2
  lda [tHeader],y
  and #255
  sta tEnd
  jeq tree_next
  clc
  adc tCur
  jmi tree_next
  jeq tree_next
  lda tCode
  sta tJump
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
  lda tCur
  jmi tree_left
  lda #128
  sec
  sbc tCur
  cmp tEnd
  jcs tree_ready
  ; 右端はROM内のsuffixから入る。端の余分な1byteだけ復元する。
  sta tTemp
  bit #1
  beq :+
  lda tDest
  clc
  adc tTemp
  sta tGuard
  inc tGuardFlag
:
  lda tTemp
  inc
  lsr
  tay
  asl
  sta tEnd
  lda [tHint],y
  and #255
  clc
  adc tCode
  sta tJump
  jmp tree_ready
tree_left:
  lda tDest
  sec
  sbc tCur
  dec
  sta tGuard
  lda tCur
  and #1
  sta tGuardFlag
  lda tCode
  cmp tLastCode
  bne tree_miss
  lda tCode+2
  cmp tLastBank
  bne tree_miss
  lda tCur
  cmp tLastCur
  bne tree_miss
  lda tLastLength
  sta tLength
dense_tree_cache_hit:
  jmp tree_buffer_ready
tree_miss:
  lda tCur
  eor #$ffff
  inc
  lsr
  tay
  lda [tHint],y
  and #255
  sta tLength
  jeq tree_next
  jsl sa1_dma_try_begin
  bcc dense_tree_copy_cpu
dense_tree_copy_dma:
  lda tLength
  sta $2238
  lda tCode
  sta $2232
  sep #$20
  lda tCode+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0500
  sta $2235
  jsl sa1_dma_end
  bra tree_patch
dense_tree_copy_cpu:
  sep #$20
  lda #$54
  sta $07e8
  stz $07e9
  lda tCode+2
  sta $07ea
  lda #$6b
  sta $07eb
  rep #$30
  phb
  ldx tCode
  ldy #$0500
  lda tLength
  dec
  jsl $0007e8
  plb
tree_patch:
  ldx tLength
  sep #$20
  lda #$5c
  sta $0500,x
  stz $0501,x
  lda #7
  sta $0502,x
  stz $0503,x
  rep #$20
  lda tCode
  sta tLastCode
  lda tCode+2
  sta tLastBank
  lda tCur
  sta tLastCur
  lda tLength
  sta tLastLength
tree_buffer_ready:
  lda #$0500
  sta tJump
  stz tJump+2
tree_ready:
  lda tDest
  clc
  adc tEnd
  sec
  sbc #2
  sta tSP
  ; 左clipの末尾wordはlow byteが窓の直前、high byteだけが可視の場合がある。
  ; その場合はhigh側の窓を選ぶ。右clipのhigh側は画面外なのでlow側を選ぶ。
  ldx tCur
  bpl :+
  inc
:
  .repeat 13
    lsr
  .endrepeat
  sta tMap
  lda tRawBank
  sec
  sbc #$40
  asl
  asl
  asl
  clc
  adc tMap
  sep #$20
  sta f:$002225
  lda tRawBank
  pha
  plb
  rep #$20
  lda tGuardFlag
  beq :+
  ldx tGuard
  sep #$20
  lda a:$0000,x
  sta tByte
  rep #$20
:
  ; IRQの復帰先がBW-RAM stackにならないよう、描画中だけSEIにする。
  sei
  lda tSP
  ldx tCur
  bpl :+
  inc
  and #$1fff
  clc
  adc #$6000
  bra tree_sp_ready
:
  and #$1fff
  clc
  adc #$6001
tree_sp_ready:
  tcs
  ldx tDest
dense_tree_row_begin:
  jml [$00ac]
dense_tree_row_done:
  lda tSaved
  tcs
  lda tGuardFlag
  beq :+
  ldx tGuard
  sep #$20
  lda tByte
  sta a:$0000,x
  rep #$20
:
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  cli
tree_next:
  lda tChain
  clc
  adc #11
  sta tChain
  dec tCount
  jne tree_row
  sep #$20
  lda #0
  sta f:$002225
  rep #$30
  plb
  plp
  sec
  rtl
