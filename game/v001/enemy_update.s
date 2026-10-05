.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _monosh_enemy_fast_advance, _fx_enemy_em1_update
.import _monosh_enemies, _monosh_enemy_active_count_value, _monosh_enemy_paths
.import _monosh_enemy_em1_phase, _monosh_enemy_ground_bottom, _monosh_bom_geometry
.import _monosh_ground_screen_delta, _monosh_enemy_player_hit
.import _monosh_player_x, _monosh_player_bottom
.import _monosh_enemy_fire_em0_fast, _fx_em0_geometry, _fx_enemy_remove
.import _fx_enemy_em1_update_reference, _fx_enemy_fire_em1
.importzp c_sp
.segment "ZEROPAGE"
ae: .res 2
.segment "CODE"
.a8
.i8
_monosh_enemy_fast_advance:
  php
  rep #$30
  stz $0360
  lda #_monosh_enemies
  sta ae
  lda _monosh_player_x
  lsr
  clc
  adc #46
  sta $0366
  lda _monosh_player_bottom
  sec
  sbc #20
  sta $0368
advance_loop:
  lda _monosh_enemy_active_count_value
  and #$ff
  cmp $0360
  jeq advance_done
  ldy #1
  lda (ae),y
  and #$ff
  cmp #5
  beq em0
  cmp #2
  jeq explosion
  jmp advance_next
em0:
  ldy #7
  lda (ae),y
  and #$ff
  beq no_fire
  dec
  bne no_fire
  sta $0364
  lda ae
  jsr pointer_arg
  jsr _monosh_enemy_fire_em0_fast
  rep #$30
  bra step_frame
no_fire:
  sta $0364
step_frame:
  ldy #3
  lda (ae),y
  inc
  and #$ff
  sep #$20
  sta (ae),y
  rep #$20
  sta $0362
  ldy #2
  lda (ae),y
  and #$ff
  asl
  asl
  tax
  lda _monosh_enemy_paths+2,x
  and #$ff
  cmp $0362
  jcc advance_remove
  jeq advance_remove
  lda ae
  jsr pointer_arg
  jsr _fx_em0_geometry
  rep #$30
  ldy #7
  lda $0364
  sep #$20
  sta (ae),y
  ldy #6
  lda (ae),y
  bne em0_next
  ldy #4
  lda (ae),y
  sec
  sbc $0366
  cmp #36
  bcs em0_next
  iny
  lda (ae),y
  sec
  sbc $0368
  cmp #53
  bcs em0_next
  lda #1
  sta _monosh_enemy_player_hit
em0_next:
  rep #$20
  jmp advance_next
explosion:
  ldy #3
  lda (ae),y
  and #$ff
  jeq advance_remove
  dec
  sep #$20
  sta (ae),y
  rep #$20
  and #$ff
  jeq advance_remove
  ldy #6
  lda (ae),y
  and #$ff
  cmp #2
  jcc advance_remove
  dec
  sta $0362
  sep #$20
  sta (ae),y
  rep #$20
  tax
  lda _monosh_enemy_ground_bottom,x
  clc
  adc _monosh_ground_screen_delta
  and #$ff
  sta $0364
  ldy #7
  lda (ae),y
  and #$ff
  beq land
  sta $036a
  ldy #5
  lda (ae),y
  and #$ff
  cmp $0364
  bcs land
  clc
  adc #13
  sec
  sbc $036a
  cmp $0364
  bcc falling
  lda $0364
falling:
  sep #$20
  sta (ae),y
  ldy #7
  lda $036a
  dec
  sta (ae),y
  rep #$20
  bra explosion_shape
land:
  lda $0364
  sep #$20
  ldy #5
  sta (ae),y
  ldy #7
  lda #0
  sta (ae),y
  rep #$20
explosion_shape:
  lda $0362
  asl
  tax
  lda _monosh_bom_geometry,x
  ldy #8
  sta (ae),y
advance_next:
  lda ae
  clc
  adc #10
  sta ae
  inc $0360
  jmp advance_loop
advance_remove:
  lda $0360
  sep #$30
  jsr _fx_enemy_remove
  rep #$30
  jmp advance_loop
advance_done:
  plp
  rts
; 16bitポインタをcc65 AXへ渡す。戻り時はA/X8bit。
pointer_arg:
  pha
  xba
  and #$ff
  tax
  pla
  sep #$30
  rts

.a8
.i8
_fx_enemy_em1_update:
  php
  rep #$30
  and #$ff
  sta $0370
  asl
  tax
  lda _monosh_enemy_em1_phase+1,x
  and #$ff
  sta $0372
  cmp #1
  beq opening
  cmp #3
  beq opening
  cmp #5
  jne em1_reference
opening:
  lda _monosh_enemy_em1_phase,x
  inc
  and #$ff
  sta $0374
  sep #$20
  sta _monosh_enemy_em1_phase,x
  rep #$20
  dec
  and #$ff
  sta $0374
  ldy #0
  lda (c_sp),y
  sta ae
  lda $0374
  cmp #122
  bcs close
  tax
  lda f:$7f0000+open_poses,x
  sep #$20
  ldy #7
  sta (ae),y
  rep #$20
  ldy #2
  lda (ae),y
  and #3
  ldx #60
  cmp #0                    ; LDXのZでlaneを判定しない。
  beq target
  ldx #66
  cmp #2
  beq target
  ldx #72
target:
  cpx $0374
  bne em1_done
  lda ae
  jsr pointer_arg
  jsr _fx_enemy_fire_em1
  rep #$30
  bra em1_done
close:
  lda $0370
  asl
  tax
  lda $0372
  inc
  xba
  sta _monosh_enemy_em1_phase,x
  ldy #7
  sep #$20
  lda #0
  sta (ae),y
  rep #$20
em1_done:
  inc c_sp
  inc c_sp
  plp
  rts
em1_reference:
  lda $0370
  plp
  jmp _fx_enemy_em1_update_reference
open_poses:
  .repeat 30,I
    .byte I/6+1
  .endrepeat
  .repeat 60
    .byte $85
  .endrepeat
  .repeat 30,I
    .byte 5-I/6
  .endrepeat
  .byte 0,0
.endif
