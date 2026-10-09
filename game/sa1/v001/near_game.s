.setcpu "65816"
.smart
.macpack longbranch
.export sa1_near_row: far
.segment "BOOT"
ncode=$a0
ntable=$a4
nsourceWord=$a6
ndest=$a8
nremaining=$aa
nchunk=$ac
nstart=$ae
nlength=$b0
ninitial=$b2
sa1_near_row:
  rep #$30
  lda $010a
  and #3
  sta nstart
  asl
  asl
  asl
  clc
  adc nstart
  adc $e4                     ; phase * 9 + background row
  asl
  asl
  tax
  lda f:$fe0000,x
  sta ncode
  lda f:$fe0002,x
  sta ntable
  lda $e6                     ; framebuffer row start
  clc
  adc $d0
  sta ndest
  lda $d2
  sec
  sbc $d0
  lsr
  sta nremaining
  lda $d0
  asl
  clc
  adc $e8
  and #511
  lsr
  lsr
  sta nsourceWord
near_chunk:
  lda #128
  sec
  sbc nsourceWord
  cmp #17
  bcc :+
  lda #16
:
  cmp nremaining
  bcc :+
  lda nremaining
:
  sta nchunk
  lda nsourceWord
  asl
  asl
  clc
  adc ntable
  tax
  lda f:$fe0000,x
  sta nstart
  lda f:$fe0002,x
  sta ninitial
  lda nchunk
  asl
  asl
  clc
  adc ntable
  sta nlength
  lda nsourceWord
  asl
  asl
  clc
  adc nlength
  tax
  lda f:$fe0000,x
  sec
  sbc nstart
  sta nlength
  jeq near_advance
  sta $2238
  lda ncode
  clc
  adc nstart
  sta $2232
  sep #$20
  lda #$fe
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0700
  sta $2235
  sta $07f1
  sep #$20
  stz $07f3
  lda #$84
  sta $2230
  rep #$20
  ldx nlength
  sep #$20
  lda #$6b
  sta $0700,x
  rep #$20
  lda nsourceWord
  asl
  sta nstart
  lda ndest
  sec
  sbc nstart
  tax
  sep #$20
  lda #$40
  pha
  plb
  rep #$20
  lda ninitial
  jsr $07f0
  sep #$20
  lda #0
  pha
  plb
  rep #$20
near_advance:
  lda nchunk
  asl
  clc
  adc ndest
  sta ndest
  lda nsourceWord
  clc
  adc nchunk
  and #127
  sta nsourceWord
  lda nremaining
  sec
  sbc nchunk
  sta nremaining
  jne near_chunk
  rtl
