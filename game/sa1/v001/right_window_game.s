; IRAMの末尾に一行を置く。0800..0FFFは読出し0・書込み無視で右端を捨てる。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_right_clip_draw: far
.segment "GSU"
rwChain=$80
rwCode=$84
rwDest=$88
rwLimit=$8a
rwStart=$8c
rwExtent=$90
sa1_right_clip_draw:
  rep #$30
  phb
  ldx #$0780
  ldy #$2c00
  lda #127
  mvn #$00,#$43
  plb
  lda $a0
  asl
  sta rwLimit
  asl
  asl
  clc
  adc rwLimit
  adc $a0
  clc
  adc $24
  sta rwChain
  lda $26
  sta rwChain+2
rw_row:
  ldy #1
  lda [rwChain],y
  clc
  adc $f8
  sta rwDest
  lda [rwChain],y
  and #127
  clc
  adc $48
  sta rwLimit
  lda #128
  sec
  sbc rwLimit
  jmi rw_next
  jeq rw_next
  sta rwLimit
  lda #$0800
  sec
  sbc rwLimit
  sta rwStart
  ldy #8
  lda [rwChain],y
  sta rwCode
  sta $0701
  iny
  iny
  sep #$20
  lda [rwChain],y
  sta rwCode+2
  sta $0703
  lda #$5c
  sta $0700
  rep #$30
.ifdef SA1_RIGHT_WINDOW_DIRECT
  lda [rwCode]
  and #255
  cmp #$6b
  jeq rw_next
  lda rwCode
  sec
  sbc #1
  sta rwExtent
  lda rwCode+2
  sta rwExtent+2
  lda [rwExtent]
  and #255
  cmp rwLimit
  bcc rw_direct
  beq rw_direct
.endif
  phb
  ldx rwDest
  ldy rwStart
  lda rwLimit
  dec
  pha
  lda $0102
  and #3
  cmp #1
  beq rw_load41
  cmp #2
  beq rw_load42
  cmp #3
  beq rw_load43
  pla
  mvn #$40,#$00
  bra rw_loaded
rw_load41:
  pla
  mvn #$41,#$00
  bra rw_loaded
rw_load42:
  pla
  mvn #$42,#$00
  bra rw_loaded
rw_load43:
  pla
  mvn #$43,#$00
rw_loaded:
  ; MVNでDB=0。2KiB IRAMの末尾へ寄せて元のROMコードを実行する。
  lda rwStart
  tax
  jsl $000700
  ldx rwStart
  ldy rwDest
  lda rwLimit
  dec
  pha
  lda $0102
  and #3
  cmp #1
  beq rw_store41
  cmp #2
  beq rw_store42
  cmp #3
  beq rw_store43
  pla
  mvn #$00,#$40
  bra rw_stored
rw_store41:
  pla
  mvn #$00,#$41
  bra rw_stored
rw_store42:
  pla
  mvn #$00,#$42
  bra rw_stored
rw_store43:
  pla
  mvn #$00,#$43
rw_stored:
  plb
.ifdef SA1_RIGHT_WINDOW_DIRECT
  bra rw_next
rw_direct:
  phb
  sep #$20
  lda $0102
  pha
  plb
  rep #$20
  ldx rwDest
  jsl $000700
  plb
.endif
rw_next:
  lda rwChain
  clc
  adc #11
  sta rwChain
  inc $a0
  lda $a0
  cmp $a2
  jcc rw_row
  phb
  ldx #$2c00
  ldy #$0780
  lda #127
  mvn #$43,#$00
  plb
  sec
  rtl
