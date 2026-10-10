; ゲーム状態だけをBW43へ複製し、7枚の描画領域を保持する。
.setcpu "65816"
.smart
.import sa1_game_frame, _fx_read_input, _fx_build_ground, _fx_buttons
.import _fx_packet_count, _fx_packet, fx_obj_next, player4_next
.import _fx_far_u_acc, _monosh_ground_offset, _fx_ground_phase, _fx_ground_world_phase
.import _fx_audio_events, _monosh_player_state, _monosh_player_stumble
.import _monosh_boss_state, _monosh_runtime_paused
.importzp c_sp
.export _fx_frame, sa1_game_call: far, sa1_game_input
.segment "BSS"
game_initialized: .res 2
.segment "CODE"
.a8
.i8
_fx_frame:
  jsl game_compact_frame
  rts
sa1_game_call:
  sep #$30
  jsr sa1_game_frame
  rep #$30
  rtl
sa1_game_input:
  php
  rep #$20
  lda f:$435200
  sta _fx_buttons
  plp
  rts
.segment "GSU"
game_compact_frame:
  php
  jsl $7f0000+game_read_input
  rep #$30
  lda f:$7e0000+game_initialized
  bne game_initialized_ok
  jsl game_clone
  lda #1
  sta f:$7e0000+game_initialized
game_initialized_ok:
  lda f:$7e0000+_fx_buttons
  sta f:$435200
  lda #1
  sta f:$0031a0
  sep #$20
  lda #$80
  sta f:$002200
  rep #$30
game_wait:
.ifdef SA1_GAME_WAIT_WAI
  jsl $7f0000+game_wait_idle
.else
  lda f:$0031a0
  bne game_wait
.endif
  jsl game_outputs
  jsl $7f0000+game_build_ground
  plp
  rtl
.segment "CODE"
.ifdef SA1_GAME_WAIT_WAI
game_wait_idle:
  php
  sei
game_wait_sleep:
  lda f:$0031a0
  beq game_wait_awake
  wai
  cli
  sei
  bra game_wait_sleep
game_wait_awake:
  plp
  rtl
.endif
game_read_input:
  sep #$30
  jsr _fx_read_input
  rep #$30
  rtl
game_build_ground:
  sep #$30
  jsr _fx_build_ground
  rep #$30
  rtl
.segment "GSU"
game_clone:
  php
  phb
  sei
  rep #$30
game_wait_boot:
  lda f:$0031a2
  beq game_wait_boot
  ldx #$6000
  ldy #$6000
  lda #$1bff
  mvn #$7e,#$43
  ldx #0
  ldy #$5100
  lda #255
  mvn #$7e,#$43
  lda #$7c00
  sta f:$435100+c_sp
  lda #$a55a
  ldx #0
game_stack_guards:
  sta f:$437b00,x
  sta f:$437e00,x
  inx
  inx
  cpx #64
  bcc game_stack_guards
  plb
  plp
  rtl
game_outputs:
  php
  phb
  rep #$30
  lda f:$430000+_fx_packet_count
  sta f:$7e0000+_fx_packet_count
  asl
  asl
  clc
  adc f:$430000+_fx_packet_count
  asl
  beq game_no_packet
  dec
  ldx #_fx_packet
  ldy #_fx_packet
  mvn #$43,#$7e
game_no_packet:
  ldx #fx_obj_next
  ldy #fx_obj_next
  lda #135
  mvn #$43,#$7e
  lda f:$430000+player4_next
  sta f:$7e0000+player4_next
  lda f:$430000+_fx_far_u_acc
  sta f:$7e0000+_fx_far_u_acc
  lda f:$430002+_fx_far_u_acc
  sta f:$7e0002+_fx_far_u_acc
  sep #$20
  .macro COPY_BYTE source
    lda f:$430000+source
    sta f:$7e0000+source
  .endmacro
  COPY_BYTE _monosh_ground_offset
  COPY_BYTE _fx_ground_phase
  COPY_BYTE _fx_ground_world_phase
  COPY_BYTE _monosh_player_state
  COPY_BYTE _monosh_player_stumble
  COPY_BYTE _monosh_boss_state
  COPY_BYTE _monosh_runtime_paused
  lda f:$430000+_fx_audio_events
  sta f:$7e0000+_fx_audio_events
  lda #0
  sta f:$430000+_fx_audio_events
  plb
  plp
  rtl
