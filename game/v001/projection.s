.setcpu "65816"
.smart
.export _monosh_project_x, fx_project16
.importzp c_sp
.segment "CODE"
.a8
.i8
_monosh_project_x:
  php
  rep #$30
  stz $018a
  and #$ff
  cmp #111
  bcc :+
  lda #110
:
  sta $0180
  stz $0182
  ldy #0
  lda (c_sp),y
  bra prepare_world
fx_project16:
  php
  rep #$30
  pha
  txa
  sta $0180
  lda #1
  sta $018a
  stz $0182
  pla
prepare_world:
  bpl positive
  inc $0182
  eor #$ffff
  inc
positive:
  sta $0184
  and #$ff
  sta $0186
  lda $0180
  xba
  ora $0186
  tax
  lda f:$7f0000+projection_rows,x
  and #$ff
  sta $0186
  lda $0180
  asl
  tax
  lda f:$7f0000+projection_scales,x
  sta $0188
  lda $0184
  xba
  and #$ff
  tax
  beq signed_result
  lda $0188
  cmp #256
  bcs saturated
add_high:
  lda $0186
  clc
  adc $0188
  cmp #255
  bcs saturated
  sta $0186
  dex
  bne add_high
  bra signed_result
saturated:
  lda #255
  sta $0186
signed_result:
  lda $0182
  beq :+
  lda $0186
  eor #$ffff
  inc
  sta $0186
:
  lda $018a
  beq c_return
  lda $0186
  plp
  rts
c_return:
  lda c_sp
  clc
  adc #2
  sta c_sp
  lda $0186
  pha
  xba
  and #$ff
  tax
  pla
  plp
  rts
projection_rows:
  .incbin "assets/projection_rows.bin"
projection_scales:
  .incbin "assets/projection_scales.bin"
