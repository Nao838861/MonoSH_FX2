.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _monosh_enemy_fast_update_bullets
.import _monosh_enemy_bullets, _monosh_enemy_bullet_count, _monosh_enemy_player_hit
.import _boss_dda_phase, _boss_dda_x, _boss_dda_y
.import _monosh_player_x, _monosh_player_bottom
.segment "CODE"
.a8
.i8
_monosh_enemy_fast_update_bullets:
  php
  rep #$30
  stz $0330                 ; slot
  stz $0332                 ; record offset (7byte)
  lda _monosh_player_x
  bpl positive
  eor #$ffff
  inc
  lsr
  eor #$ffff
  inc
  bra center
positive:
  lsr
center:
  clc
  adc #50
  sta $0334
  lda _monosh_player_bottom
  sec
  sbc #20
  sta $0336
  sep #$20
bullet:
  lda $0330
  cmp _monosh_enemy_bullet_count
  jcs done
  ldx $0332
  ldy $0330
  stz $033a
  lda _monosh_enemy_bullets+6,x
  bmi depth
  inc
  and #63
  sta _monosh_enemy_bullets+6,x
depth:
  lda _monosh_enemy_bullets+3,x
  beq near
  dec _monosh_enemy_bullets+3,x
  bra move
near:
  lda _monosh_enemy_bullets,x
  cmp #2
  beq expired
  lda _monosh_enemy_bullets+6,x
  bpl near_active
  lda _boss_dda_phase,y
  and #1
  beq move
near_active:
  lda #2
  sta _monosh_enemy_bullets,x
  bra move
expired:
  inc $033a
move:
  lda _monosh_enemy_bullets+1,x
  clc
  adc _monosh_enemy_bullets+4,x
  sta _monosh_enemy_bullets+1,x
  lda _monosh_enemy_bullets+2,x
  clc
  adc _monosh_enemy_bullets+5,x
  sta _monosh_enemy_bullets+2,x
  lda _monosh_enemy_bullets+6,x
  bpl check_y
  lda _boss_dda_phase,y
  eor #1
  sta _boss_dda_phase,y
  and #1
  beq check_y
  lda _monosh_enemy_bullets+1,x
  clc
  adc _boss_dda_x,y
  sta _monosh_enemy_bullets+1,x
  lda _monosh_enemy_bullets+2,x
  clc
  adc _boss_dda_y,y
  sta _monosh_enemy_bullets+2,x
check_y:
  lda _monosh_enemy_bullets+2,x
  cmp #224
  bcc collision
  lda #1
  sta $033a
collision:
  lda $033a
  bne remove
  lda _monosh_enemy_bullets,x
  cmp #2
  bne next
  lda _monosh_enemy_bullets+3,x
  bne next
  lda _monosh_enemy_bullets+1,x
  sec
  sbc $0334
  cmp #28
  bcs next
  lda _monosh_enemy_bullets+2,x
  sec
  sbc $0336
  cmp #61
  bcs next
  lda #1
  sta _monosh_enemy_player_hit
next:
  rep #$20
  inc $0330
  lda $0332
  clc
  adc #7
  sta $0332
  sep #$20
  jmp bullet
remove:
  dec _monosh_enemy_bullet_count
  rep #$20
  lda _monosh_enemy_bullet_count
  and #$ff
  sta $0338
  asl
  asl
  asl
  sec
  sbc $0338
  tay
  lda _monosh_enemy_bullets,y
  sta _monosh_enemy_bullets,x
  lda _monosh_enemy_bullets+2,y
  sta _monosh_enemy_bullets+2,x
  lda _monosh_enemy_bullets+4,y
  sta _monosh_enemy_bullets+4,x
  sep #$20
  lda _monosh_enemy_bullets+6,y
  sta _monosh_enemy_bullets+6,x
  lda #0
  sta _monosh_enemy_bullets,y
  ldx $0330
  ldy $0338
  lda _boss_dda_phase,y
  sta _boss_dda_phase,x
  lda _boss_dda_x,y
  sta _boss_dda_x,x
  lda _boss_dda_y,y
  sta _boss_dda_y,x
  jmp bullet
done:
  plp
  rts
.endif
