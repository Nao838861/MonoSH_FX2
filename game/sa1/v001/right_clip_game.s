; 元の行コードの可視部分だけをI-RAMへ複写し、末尾へRTLを置く。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_right_clip_draw: far
.import __RIGHTJIT_LOAD__, __RIGHTJIT_SIZE__
.import sa1_dma_try_begin: far, sa1_dma_end: far
.segment "GSU"
sa1_right_clip_draw:
  rep #$30
  jsl sa1_dma_try_begin
  bcc right_load_cpu
  lda #__RIGHTJIT_SIZE__
  sta $2238
  lda #.loword(__RIGHTJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__RIGHTJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  jml right_entry
right_load_cpu:
  phb
  lda #__RIGHTJIT_SIZE__-1
  ldx #.loword(__RIGHTJIT_LOAD__)
  ldy #$0300
  mvn #^__RIGHTJIT_LOAD__,#$00
  plb
  jml right_entry
.segment "RIGHTJIT"
rightChain=$80
rightCode=$84
rightDest=$88
rightLimit=$8a
rightLength=$8c
rightGuard=$90
rightByte=$94
rightPrevious=$b6
rightPreviousBank=$b8
rightPreviousLimit=$ba
rightPreviousLength=$bc
right_entry:
  rep #$30
  lda #$ffff
  sta rightPrevious
  lda $a0
  asl
  sta rightLength
  asl
  asl
  clc
  adc rightLength
  adc $a0
  clc
  adc $24
  sta rightChain
  lda $26
  sta rightChain+2
right_row:
  ldy #1
  lda [rightChain],y
  clc
  adc $f8
  sta rightDest
  ldy #1
  lda [rightChain],y
  and #127
  clc
  adc $48
  sta rightLength
  lda #128
  sec
  sbc rightLength
  jmi right_next
  jeq right_next
  sta rightLimit
  ldy #8
  lda [rightChain],y
  sta rightCode
  iny
  iny
  lda [rightChain],y
  and #255
  sta rightCode+2
  lda rightCode
  cmp rightPrevious
  bne right_new
  lda rightCode+2
  cmp rightPreviousBank
  bne right_new
  lda rightLimit
  cmp rightPreviousLimit
  bne right_new
  lda rightPreviousLength
  sta rightLength
  jmp right_ready
right_new:
  ldy #0
  stz rightLength
right_scan:
  lda [rightCode],y
  and #255
  cmp #$6b
  beq right_scanned
  cmp #$9d
  bne right_scan_next
  iny
  lda [rightCode],y
  dey
  cmp rightLimit
  bcs right_scanned
  tya
  clc
  adc #3
  sta rightLength
right_scan_next:
  iny
  iny
  iny
  bra right_scan
right_scanned:
  lda rightCode
  sta rightPrevious
  lda rightCode+2
  sta rightPreviousBank
  lda rightLimit
  sta rightPreviousLimit
  lda rightLength
  sta rightPreviousLength
  jeq right_next
  jsl sa1_dma_try_begin
  bcc right_copy_cpu
  lda rightLength
  sta $2238
  lda rightCode
  sta $2232
  sep #$20
  lda rightCode+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0500
  sta $2235
  jsl sa1_dma_end
  bra right_patch
right_copy_cpu:
  sep #$20
  lda #$54
  sta $07e8
  stz $07e9
  lda rightCode+2
  sta $07ea
  lda #$6b
  sta $07eb
  rep #$30
  phb
  ldx rightCode
  ldy #$0500
  lda rightLength
  dec
  jsl $0007e8
  plb
right_patch:
  ldx rightLength
  sep #$20
  lda #$6b
  sta $0500,x
  rep #$20
right_ready:
  lda rightLength
  jeq right_next
  lda rightDest
  clc
  adc rightLimit
  sta rightGuard
  lda $0102
  and #255
  sta rightGuard+2
  sep #$20
  lda [rightGuard]
  sta rightByte
  phb
  lda $0102
  pha
  plb
  rep #$20
  ldx rightDest
  jsl $000500
  plb
  sep #$20
  lda rightByte
  sta [rightGuard]
  rep #$30
right_next:
  lda rightChain
  clc
  adc #11
  sta rightChain
  inc $a0
  lda $a0
  cmp $a2
  jcc right_row
  sec
  rtl
