.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _monosh_combat_fast_frame, _monosh_combat_fast_render
.import _fx_fire_actions, _monosh_combat_fire_cooldown
.import _monosh_player_x, _monosh_player_bottom, _monosh_player_state
.import _monosh_player_bullets, _monosh_player_bullet_count, _monosh_player_bullet_sizes
.import _monosh_reflected_bullets, _monosh_reflected_bullet_count
.import fx_emit_native
.segment "CODE"
.a8
.i8
_monosh_combat_fast_frame:
  php
  rep #$30
  lda _fx_fire_actions
  and #1
  bne fire
  lda _fx_fire_actions
  and #2
  beq release
  lda _monosh_combat_fire_cooldown
  and #$ff
  beq ready
  sep #$20
  dec _monosh_combat_fire_cooldown
  bra done8
release:
  sep #$20
  stz _monosh_combat_fire_cooldown
  bra done8
ready:
  sep #$20
  lda #3
  sta _monosh_combat_fire_cooldown
  rep #$20
fire:
  lda _monosh_player_bullet_count
  and #$ff
  cmp #3
  beq done
  ldx #0
find_slot:
  lda _monosh_player_bullets,x
  and #$ff
  beq spawn
  txa
  clc
  adc #5
  tax
  cmp #15
  bcc find_slot
  bra done
spawn:
  sep #$20
  lda #1
  sta _monosh_player_bullets,x
  lda _monosh_player_x
  sta _monosh_player_bullets+1,x
  lda _monosh_player_bottom
  sec
  sbc #20
  sta _monosh_player_bullets+2,x
  stz _monosh_player_bullets+3,x
  lda #2
  sta _monosh_player_bullets+4,x
  inc _monosh_player_bullet_count
done8:
  rep #$20
done:
  plp
  rts

.a8
.i8
_monosh_combat_fast_render:
  php
  rep #$30
  stz $02e0                   ; 各枠は5byte。emitのscratchと分離する。
player_loop:
  ldx $02e0
  lda _monosh_player_bullets,x
  and #$ff
  jeq player_next
  lda _monosh_player_state
  and #$ff
  bne player_size
  sep #$20
  inc _monosh_player_bullets+4,x
  lda _monosh_player_bullets+3,x
  clc
  adc #2
  sta _monosh_player_bullets+3,x
  lda _monosh_player_bullets+4,x
  cmp #25
  bcc :+
  stz _monosh_player_bullets,x
  dec _monosh_player_bullet_count
  rep #$20
  bra player_next
:
  rep #$20
player_size:
  lda _monosh_player_bullets+4,x
  and #$ff
  tay
  lda _monosh_player_bullet_sizes,y
  and #$ff
  sta $0246
  xba
  ora $0246
  sta $0246
  lda _monosh_player_bullets+1,x
  and #$ff
  sta $0242
  lda _monosh_player_bullets+2,x
  and #$ff
  sta $0244
  jsr emit_bullet
player_next:
  lda $02e0
  clc
  adc #5
  sta $02e0
  cmp #15
  jcc player_loop
  stz $02e0
reflected_loop:
  ldx $02e0
  lda _monosh_reflected_bullets,x
  and #$ff
  jeq reflected_next
  lda _monosh_reflected_bullets+1,x
  and #$ff
  sta $0242
  lda _monosh_reflected_bullets+2,x
  and #$ff
  sta $0244
  lda _monosh_player_state
  and #$ff
  bne reflected_emit
  lda _monosh_reflected_bullets+3,x
  and #$ff
  cmp #128
  bcc :+
  ora #$ff00
:
  clc
  adc $0242
  cmp #256
  bcs outside
  sta $0242
  lda _monosh_reflected_bullets+4,x
  and #$ff
  cmp #128
  bcc :+
  ora #$ff00
:
  clc
  adc $0244
  cmp #212
  bcs outside
  sta $0244
  sep #$20
  lda $0242
  sta _monosh_reflected_bullets+1,x
  lda $0244
  sta _monosh_reflected_bullets+2,x
  rep #$20
reflected_emit:
  lda #$0c0c
  sta $0246
  lda #$400a                ; flags=$40は小さい反射弾。判定矩形12x12は維持。
  sta $0248
  lda #$0200
  sta $024a
  jsr fx_emit_native
  bra reflected_next
outside:
  sep #$20
  stz _monosh_reflected_bullets,x
  dec _monosh_reflected_bullet_count
  rep #$20
reflected_next:
  lda $02e0
  clc
  adc #5
  sta $02e0
  cmp #15
  jcc reflected_loop
  plp
  rts
emit_bullet:
  lda #10
  sta $0248
  lda #$0200
  sta $024a
  jmp fx_emit_native
.endif
