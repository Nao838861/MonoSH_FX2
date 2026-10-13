; 逆順の木4は左端の可視prefixだけをIRAMへ保持する。物体内の同じ行を再利用。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dma_try_begin: far, sa1_dma_end: far
.export sa1_reverse_tree_left: far, tree_left_miss: far, tree_left_cached_ready: far
.export tree_left_copy_dma: far, tree_left_copy_cpu: far, tree_left_patch_complete: far
.export tree_left_prefix_invoke: far, tree_left_full_invoke: far
.export tree_left_prefix_done: far
.segment "GSU"
lChain=$80
lCode=$84
lDest=$88
lCur=$8a
lHeader=$8c
lHint=$90
lTemp=$94
lCount=$96
lGuard=$98
lByte=$9a
lLength=$9c
lLastCode=$a0
lLastBank=$a2
lLastCur=$a4
lLastLength=$a6
sa1_reverse_tree_left:
  rep #$30
  phb
  lda $a2
  sec
  sbc $a0
  sta lCount
  lda $a0
  asl
  sta lTemp
  asl
  asl
  clc
  adc lTemp
  adc $a0
  clc
  adc $24
  sta lChain
  stz lChain+2
  sep #$20
  lda $26
  sta lChain+2
  lda #0
  pha
  plb
  rep #$20
  lda #$ffff
  sta lLastCode
  sta lLastBank
  sta lLastCur
  stz lLastLength
left_row:
  stz lLength
  ldy #1
  lda [lChain],y
  clc
  adc $f8
  sta lDest
  lda [lChain],y
  and #127
  clc
  adc $48
  sta lCur
  ldy #8
  lda [lChain],y
  sta lCode
  sec
  sbc #3
  sta lHeader
  ldy #10
  lda [lChain],y
  and #255
  sta lCode+2
  sta lHeader+2
  ldy #2
  lda [lHeader],y
  and #255
  jeq left_next
  clc
  adc lCur
  jmi left_next
  jeq left_next
  lda lCur
  jpl left_full
.ifdef SA1_TREE_LEFT_NO_CACHE
  jmp tree_left_miss
.else
  jmp left_cache_check
.endif
left_cache_check:
  lda lCode
  cmp lLastCode
  bne tree_left_miss
  lda lCode+2
  cmp lLastBank
  bne tree_left_miss
  lda lCur
  cmp lLastCur
  bne tree_left_miss
  lda lLastLength
  sta lLength
tree_left_cached_ready:
  jmp left_buffer_ready
tree_left_miss:
  lda [lHeader]
  and #255
  sta lTemp
  asl
  clc
  adc lTemp
  tax
  lda f:$df6fe0,x
  sta lHint
  lda f:$df6fe2,x
  and #255
  sta lHint+2
  lda lCur
  eor #$ffff
  inc
  lsr
  tay
  lda [lHint],y
  and #255
  sta lLength
  jeq left_next
  jsl sa1_dma_try_begin
  bcc tree_left_copy_cpu
tree_left_copy_dma:
  lda lLength
  sta $2238
  lda lCode
  sta $2232
  sep #$20
  lda lCode+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0700
  sta $2235
  jsl sa1_dma_end
  bra left_patch
tree_left_copy_cpu:
  sep #$20
  lda #$54
  sta $07e8
  stz $07e9
  lda lCode+2
  sta $07ea
  lda #$6b
  sta $07eb
  rep #$30
  phb
  ldx lCode
  ldy #$0700
  lda lLength
  dec
  jsl $0007e8
  plb
left_patch:
  ldx lLength
  sep #$20
  lda #$6b
  sta $0700,x
  rep #$20
  lda lCode
  sta lLastCode
  lda lCode+2
  sta lLastBank
  lda lCur
  sta lLastCur
  lda lLength
  sta lLastLength
tree_left_patch_complete:
left_buffer_ready:
  lda lDest
  sec
  sbc lCur
  dec
  sta lGuard
  phb
  sep #$20
  lda $0102
  pha
  plb
  rep #$20
  lda lCur
  bit #1
  beq left_no_guard
  ldx lGuard
  sep #$20
  lda a:$0000,x
  sta lByte
  rep #$20
left_no_guard:
  ldx lDest
tree_left_prefix_invoke:
  jsl $000700
  lda lCur
  bit #1
  beq left_buffer_done
  ldx lGuard
  sep #$20
  lda lByte
  sta a:$0000,x
  rep #$20
left_buffer_done:
  plb
tree_left_prefix_done:
  bra left_next
left_full:
  sep #$20
  lda #$5c
  sta $07e8
  rep #$20
  lda lCode
  sta $07e9
  sep #$20
  lda lCode+2
  sta $07eb
  phb
  lda $0102
  pha
  plb
  rep #$20
  ldx lDest
tree_left_full_invoke:
  jsl $0007e8
  plb
left_next:
  rep #$30
  lda lChain
  clc
  adc #11
  sta lChain
  dec lCount
  jne left_row
  plb
  sec
  rtl
