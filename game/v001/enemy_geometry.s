.setcpu "65816"
.smart
.export _fx_em0_geometry
.import _monosh_enemy_paths, _monosh_enemy_geometry, _monosh_ground_screen_delta
.segment "ZEROPAGE"
ge: .res 2
gs: .res 2
.segment "CODE"
.a8
.i8
; 最終の16bit引数はcc65のAX。経路の3byte sampleを直接読む。
_fx_em0_geometry:
  php
  rep #$30
  and #$ff
  sta $0280
  txa
  and #$ff
  xba
  ora $0280
  sta ge
  ldy #2
  lda (ge),y
  and #$ff
  asl
  asl
  tax
  lda _monosh_enemy_paths,x
  sta gs
  ldy #3
  lda (ge),y
  and #$ff
  sta $0280
  asl
  clc
  adc $0280
  tay
  lda (gs),y
  and #$ff
  sta $0280
  iny
  lda (gs),y
  and #$ff
  clc
  adc _monosh_ground_screen_delta
  and #$ff
  xba
  ora $0280
  ldy #4
  sta (ge),y
  ldy #3
  lda (ge),y
  and #$ff
  sta $0280
  asl
  clc
  adc $0280
  inc
  inc
  tay
  lda (gs),y
  and #$ff
  sep #$20
  ldy #6
  sta (ge),y
  rep #$20
  and #$ff
  cmp #111
  bcc :+
  lda #110
:
  asl
  tax
  lda _monosh_enemy_geometry,x
  ldy #8
  sta (ge),y
  plp
  rts
