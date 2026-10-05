.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _fx_boss_hits
.import _monosh_player_bullet_count, _monosh_player_bullets, _monosh_combat_reflect_bullet
.import _boss_part_active, _boss_part_z, _boss_part_x, _boss_part_bottom
.import _monosh_boss_face_geometry, _monosh_boss_body_geometry
.import _monosh_boss_hp, _monosh_boss_state, _boss_death_timer, _boss_death_parts
.segment "CODE"
.a8
.i8
_fx_boss_hits:
  php
  rep #$30
  lda _monosh_player_bullet_count
  and #$ff
  jeq done
  stz $02f0                 ; 弾index
  stz $02f2                 ; 弾record offset
bullet:
  ldx $02f2
  lda _monosh_player_bullets,x
  and #$ff
  cmp #1
  jne next_bullet
  lda _monosh_player_bullets+1,x
  and #$ff
  sta $02f8
  lda _monosh_player_bullets+2,x
  and #$ff
  sta $02fa
  lda _monosh_player_bullets+3,x
  and #$ff
  asl
  sta $02fc
  lda #255
  sta $02f6                 ; best Z。等しいZは先に調べた頭を優先。
  sta $0300                 ; hit part
  stz $02f4
part:
  ldx $02f4
  lda _boss_part_active,x
  and #$ff
  cmp #1
  jne next_part
  lda _boss_part_z,x
  and #$ff
  sta $02fe
  lda $02fc
  sec
  sbc $02fe
  bpl :+
  eor #$ffff
  inc
:
  cmp #13
  jcs next_part
  lda $02fe
  cmp #111
  bcc :+
  lda #110
:
  asl
  tay
  cpx #0
  beq face
  lda _monosh_boss_body_geometry,y
  bra geometry
face:
  lda _monosh_boss_face_geometry,y
geometry:
  sta $0302
  and #$ff
  lsr
  sta $0304
  lda $0302
  xba
  and #$ff
  lsr
  sta $0306
  lda _boss_part_x,x
  and #$ff
  sta $0302
  lda $02f8
  sec
  sbc $0302
  bpl :+
  eor #$ffff
  inc
:
  cmp $0304
  bcc y_test
  jne next_part
y_test:
  lda _boss_part_bottom,x
  and #$ff
  sec
  sbc $0306
  sta $0302
  lda $02fa
  sec
  sbc $0302
  bpl :+
  eor #$ffff
  inc
:
  cmp $0306
  bcc hit
  bne next_part
hit:
  lda $02fe
  cmp $02f6
  bcs next_part
  sta $02f6
  stx $0300
next_part:
  inc $02f4
  lda $02f4
  cmp #9
  jcc part
  lda $0300
  cmp #255
  beq next_bullet
  cmp #0
  beq head_hit
  tax                      ; cc65 unsigned int: low A, high X
  lda $02f0
  sep #$30
  jsr _monosh_combat_reflect_bullet
  rep #$30
  bra next_bullet
head_hit:
  ldx $02f2
  sep #$20
  stz _monosh_player_bullets,x
  dec _monosh_player_bullet_count
  lda _monosh_boss_hp
  beq dying
  dec _monosh_boss_hp
  bne alive
dying:
  lda #2
  sta _monosh_boss_state
  stz _boss_death_timer
  stz _boss_death_parts
  rep #$20
  bra done
alive:
  rep #$20
next_bullet:
  lda $02f2
  clc
  adc #5
  sta $02f2
  inc $02f0
  lda $02f0
  cmp #3
  jcc bullet
done:
  plp
  rts
.endif
