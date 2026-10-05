.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _fx_frame
.import _fx_read_input, _fx_buttons, _fx_input, _fx_fire_actions, _old_buttons, _hit_pending
.import _monosh_runtime_paused, _monosh_runtime_frame_counter, _monosh_runtime_fire_actions
.import _ground_irq_vblank_count, _fx_ground_phase, _fx_ground_world_phase
.import _monosh_player_state, _monosh_player_x, _monosh_player_bottom, _monosh_player_stumble
.import _monosh_player_update, _monosh_player_draw_flags, _monosh_player_draw_asset
.import _monosh_ground_offset, _monosh_ground_screen_delta, _monosh_ground_depth_pointer
.import _fx_ground_camera, _fx_ground_depth_rows, _fx_far_u_acc, _fx_far_d_acc
.import _fx_draw_count, _monosh_combat_fast_frame, _monosh_combat_render
.import _monosh_enemy_frame, _monosh_stage_frame, _monosh_boss_frame
.import _monosh_enemy_render_only, _monosh_stage_render_only, _monosh_boss_render_only
.import _monosh_boss_prepare_render, _monosh_boss_state, _boss_render_camera_delta
.import _monosh_enemy_stage_complete_flag, _monosh_enemy_active_count_value
.import _monosh_enemy_bullet_count, _monosh_stage_object_count, _monosh_title_visible
.import _monosh_boss_should_restart, _monosh_stage_init, _monosh_enemy_init, _monosh_boss_init
.import _fx_build_packet, _fx_build_ground, fx_emit_native
.importzp c_sp
.macro CALL_C name
  sep #$30
  jsr name
  rep #$30
.endmacro
.segment "CODE"
.a8
.i8
_fx_frame:
  php
  rep #$30
  CALL_C _fx_read_input
  stz $02a8                 ; stage_ready
  lda _fx_buttons
  bit #$1000
  beq input
  lda _old_buttons
  bit #$1000
  bne input
  sep #$20
  lda _monosh_runtime_paused
  eor #1
  sta _monosh_runtime_paused
  rep #$20
input:
  lda _fx_buttons
  xba
  and #15                  ; SNES方向bitとMOVE_*の順序は同じ
  sep #$20
  sta _fx_input
  stz _fx_fire_actions
  rep #$20
  lda _fx_buttons
  bit #$4000
  beq auto_fire
  lda _old_buttons
  bit #$4000
  bne auto_fire
  sep #$20
  inc _fx_fire_actions
  rep #$20
auto_fire:
  lda _fx_buttons
  bit #$0080
  beq input_done
  sep #$20
  lda _fx_fire_actions
  ora #2
  sta _fx_fire_actions
  rep #$20
input_done:
  lda _fx_buttons
  sta _old_buttons
  sep #$20
  lda _fx_fire_actions
  sta _monosh_runtime_fire_actions
  lda _monosh_runtime_paused
  rep #$20
  and #$ff
  jne done
  inc _monosh_runtime_frame_counter
  inc _ground_irq_vblank_count
  lda _monosh_player_state
  and #$ff
  bne update_player
  sep #$20
  inc _fx_ground_phase
  lda _fx_ground_phase
  cmp #14
  bne :+
  stz _fx_ground_phase
:
  rep #$20
update_player:
  dec c_sp                 ; cc65のinputはstack、最後のhitはA
  sep #$20
  lda _fx_input
  sta (c_sp)
  lda _hit_pending
  CALL_C _monosh_player_update
  sep #$20
  stz _hit_pending
  rep #$20
  lda _monosh_player_bottom
  bmi low_camera
  cmp #57
  bcc low_camera
  cmp #201
  bcs high_camera
  sec
  sbc #56
  tax
  lda _fx_ground_camera,x
  and #$ff
  bra camera_target
low_camera:
  lda #0
  bra camera_target
high_camera:
  lda #64
camera_target:
  sta $02a2
  lda _monosh_ground_offset
  and #$ff
  cmp $02a2
  beq camera_done
  bcc camera_up
  dec
  bra camera_store
camera_up:
  inc
camera_store:
  sep #$20
  sta _monosh_ground_offset
  rep #$20
camera_done:
  sta $02a2
  sec
  sbc #28
  sep #$20
  sta _monosh_ground_screen_delta
  rep #$20
  lda $02a2
  .repeat 4
    asl
  .endrepeat
  sta $02a4
  asl
  asl
  clc
  adc $02a4
  adc $02a2
  adc #_fx_ground_depth_rows
  sta _monosh_ground_depth_pointer
  CALL_C _monosh_player_draw_flags
  and #$ff
  sta $02a0
  lda _monosh_player_state
  and #$ff
  bne render_combat
  lda _monosh_player_x
  sec
  sbc #128
  sta $02a6
  .repeat 4
    cmp #$8000
    ror
  .endrepeat
  clc
  adc _fx_ground_world_phase
  and #127
  sep #$20
  sta _fx_ground_world_phase
  rep #$20
  lda $02a6
  asl
  sta $02a6
  clc
  adc _fx_far_u_acc
  sta _fx_far_u_acc
  lda $02a6
  asl
  clc
  adc _fx_far_d_acc
  sta _fx_far_d_acc
render_combat:
  sep #$20
  stz _fx_draw_count
  rep #$20
  lda _monosh_player_state
  and #$ff
  bne combat_only
  lda _monosh_player_stumble
  and #$ff
  bne combat_only
  CALL_C _monosh_combat_fast_frame
combat_only:
  CALL_C _monosh_combat_render
  lda _monosh_player_x
  sta $0242
  lda #201
  sta $0244
  lda #$0820
  sta $0246
  lda #38
  sta $0248
  stz $024a
  jsr fx_emit_native
  lda _monosh_player_state
  and #$ff
  jne frozen
  CALL_C _monosh_enemy_frame
  sep #$20
  sta _hit_pending
  rep #$20
  lda _monosh_boss_state
  and #$ff
  bne boss
  CALL_C _monosh_stage_frame
  sep #$30
  ldx _hit_pending
  bne :+
  sta _hit_pending
:
  rep #$30
  lda _monosh_enemy_stage_complete_flag
  and #$ff
  beq player
  lda _monosh_enemy_active_count_value
  and #$ff
  bne player
  lda _monosh_enemy_bullet_count
  and #$ff
  bne player
  lda _monosh_stage_object_count
  and #$ff
  bne player
  inc $02a8
boss:
  lda c_sp
  sec
  sbc #3
  sta c_sp
  ldy #0
  lda _monosh_player_x
  sta (c_sp),y
  sep #$20
  ldy #2
  lda $02a8
  sta (c_sp),y
  rep #$20
  lda _monosh_player_bottom
  pha
  xba
  and #$ff
  tax
  pla
  CALL_C _monosh_boss_frame
  sep #$20
  lda _monosh_ground_screen_delta
  sta _boss_render_camera_delta
  rep #$20
  CALL_C _monosh_boss_prepare_render
  jsr _monosh_boss_render_only
  bra player
frozen:
  CALL_C _monosh_enemy_render_only
  CALL_C _monosh_stage_render_only
  jsr _monosh_boss_render_only
player:
  CALL_C _monosh_player_draw_asset
  and #$ff
  sta $0248
  lda $02a0
  xba
  ora $0248
  sta $0248
  lda _monosh_player_x
  sta $0242
  lda _monosh_player_bottom
  sta $0244
  lda #$3020
  sta $0246
  lda #$0200
  sta $024a
  jsr fx_emit_native
  lda _monosh_title_visible
  and #$ff
  beq restart
  lda #132
  sta $0242
  lda #133
  sta $0244
  lda #$2658
  sta $0246
  lda #42
  sta $0248
  stz $024a
  jsr fx_emit_native
restart:
  lda _monosh_boss_state
  and #$ff
  cmp #3
  bne packet
  CALL_C _monosh_boss_should_restart
  and #$ff
  beq packet
  CALL_C _monosh_stage_init
  CALL_C _monosh_enemy_init
  CALL_C _monosh_boss_init
  sep #$20
  stz _hit_pending
  rep #$20
packet:
  jsr _fx_build_packet
  jsr _fx_build_ground
done:
  plp
  rts
.endif
