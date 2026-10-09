; PPUが変換DMAを使う間も、SA-1の通常命令で変更行を消去できる。
.setcpu "65816"
.smart
.export sa1_cpu_clear_line: far, sa1_cpu_far_line: far
.segment "BOOT"
sa1_cpu_clear_line:
  rep #$30
  lda $ea                       ; bgfirst: tile幅なので4Bの倍数
  lsr
  tax
  lda f:fill_starts,x
  sta $07f1
  sep #$20
  lda #^fill_body
  sta $07f3
  lda $0102
  pha
  plb
  rep #$20
  ldx $e6                       ; bgdest
  lda #0
  jsr $07f0
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  rtl

sa1_cpu_far_line:
  rep #$30
  lda $e8
  clc
  adc $d0
  and #255
  sta $f0
  lda #256
  sec
  sbc $f0
  cmp $ee
  bcc :+
  lda $ee
:
  sta $ea
  lda $e4
  xba
  clc
  adc $ec
  adc $f0
  tax
  lda $e6
  clc
  adc $d0
  tay
  sep #$20
  lda #$54
  sta $07ec
  lda $0102
  sta $07ed
  lda #$de
  sta $07ee
  lda #$6b
  sta $07ef
  rep #$20
  lda $ea
  dec
  jsl $0007ec
  lda $ee
  sec
  sbc $ea
  beq far_cpu_return
  pha
  lda $e4
  xba
  clc
  adc $ec
  tax
  lda $e6
  clc
  adc $d0
  adc $ea
  tay
  pla
  dec
  jsl $0007ec
far_cpu_return:
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  rtl
fill_starts:
.repeat 33,I
  .word .loword(fill_body)+(64-2*I)*3
.endrepeat
fill_body:
.repeat 64,I
  sta a:126-I*2,x
.endrepeat
  rtl
