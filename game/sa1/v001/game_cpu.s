; ゲーム状態をBW40へ分離し、SA-1へ一世代の更新を依頼する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_game_frame, _fx_read_input, _fx_build_ground, _fx_buttons
.import _fx_packet_count, _fx_packet, fx_obj_next, player4_next
.import _fx_far_u_acc, _monosh_ground_offset, _fx_ground_phase, _fx_ground_world_phase
.import _fx_audio_events
.ifdef SA1_GAME_STAGE_OVERLAP
.import pipe_stage_convert: far
.endif
.export _fx_frame, sa1_game_call: far, sa1_game_input
.segment "BSS"
game_initialized: .res 2
.segment "CODE"
.a8
.i8
_fx_frame:
  php
  jsr _fx_read_input
  rep #$30
  lda game_initialized
  bne game_initialized_ok
  jsl game_clone
  inc game_initialized
game_initialized_ok:
  lda _fx_buttons
  sta f:$40a200
  lda #1
  sta f:$0031a0
  sep #$20
  lda #$80
  sta f:$002200
  rep #$30
.ifdef SA1_GAME_STAGE_OVERLAP
  php
  sei
  jsl $c10000+pipe_stage_convert
  plp
.endif
game_wait:
  lda f:$0031a0
  bne game_wait
  jsl game_outputs
  sep #$30
  jsr _fx_build_ground
  plp
  rts
sa1_game_call:
  sep #$30
  jsr sa1_game_frame
  rep #$30
  rtl
sa1_game_input:
  php
  rep #$20
  lda f:$40a200
  sta _fx_buttons
  plp
  rts
.segment "GSU"
.a16
.i16
game_clone:
  php
  phb
  sei
  rep #$30
game_wait_boot:
  lda f:$0031a2
  beq game_wait_boot
  ldx #0
  ldy #0
  lda #$ffff
  mvn #$7e,#$40
  plb
  plp
  rtl
; CPUに必要な出力だけ戻す。全ゲーム状態のコピーは行わない。
game_outputs:
  php
  phb
  rep #$30
  lda f:$400000+_fx_packet_count
  sta f:$7e0000+_fx_packet_count
  asl
  asl
  clc
  adc f:$400000+_fx_packet_count
  asl
  beq game_no_packet
  dec
  ldx #_fx_packet
  ldy #_fx_packet
  mvn #$40,#$7e
game_no_packet:
  ldx #fx_obj_next
  ldy #fx_obj_next
  lda #135
  mvn #$40,#$7e
  lda f:$400000+player4_next
  sta f:$7e0000+player4_next
  lda f:$400000+_fx_far_u_acc
  sta f:$7e0000+_fx_far_u_acc
  lda f:$400002+_fx_far_u_acc
  sta f:$7e0002+_fx_far_u_acc
  lda f:$400000+_monosh_ground_offset
  sta f:$7e0000+_monosh_ground_offset
  sep #$20
  lda f:$400000+_fx_ground_phase
  sta f:$7e0000+_fx_ground_phase
  lda f:$400000+_fx_ground_world_phase
  sta f:$7e0000+_fx_ground_world_phase
  lda f:$400000+_fx_audio_events
  sta f:$7e0000+_fx_audio_events
  lda #0
  sta f:$400000+_fx_audio_events
  plb
  plp
  rtl
