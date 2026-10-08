; worldY(8bit) * scale(9bit) >> 8 をSNES乗算器で求める。
; cc65 fastcall: A=Z、X=worldY、戻り値A/X=unsigned int。
.import _monosh_boss_explosion_scale_low
.export _fx4_explosion_lift, math4_lift_result
.segment "CODE"
.a8
.i8
_fx4_explosion_lift:
  php
  sta $0380
  stx $0381
  rep #$30
  lda $0380
  and #$ff
  tax
  lda _monosh_boss_explosion_scale_low,x
  and #$ff
  xba
  sta $0382
  lda $0381
  and #$ff
  ora $0382
  sta f:$004202
  lda $0380
  and #$ff
  cmp #13
  bcc math_high_scale4
  lda #0
  bra math_scale_ready4
math_high_scale4:
  lda $0381
  and #$ff
math_scale_ready4:
  sta $0382
  lda f:$004216
  xba
  and #$ff
  clc
  adc $0382
  asl
math4_lift_result:
  pha
  xba
  and #$ff
  tax
  pla
  plp
  rts
