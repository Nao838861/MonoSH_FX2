.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _monosh_player_update
.import _monosh_player_update_reference, _monosh_player_x, _monosh_player_bottom
.import _monosh_player_state, _monosh_player_invuln, _monosh_player_stumble, _monosh_player_pose
.import _monosh_stage_title_timer, _intro_timer, _movement_fraction
.import _player_fy, _player_flip, _player_run_phase, _pose_x_01, _pose_x_12, _pose_x_23
.importzp c_sp
.segment "CODE"
.a8
.i8
_monosh_player_update:
  php
  rep #$30
  and #$ff
  sta $0340
  lda _monosh_player_state
  and #$ff
  jne reference
  lda _monosh_player_stumble
  and #$ff
  jne reference
  lda _intro_timer
  and #$ff
  jne reference
  lda _monosh_stage_title_timer
  and #$ff
  jne reference
  lda $0340
  cmp #2
  jeq reference
  cmp #1
  bne fast
  lda _monosh_player_invuln
  and #$ff
  jeq reference
fast:
  sep #$20
  lda _monosh_player_invuln
  beq :+
  cmp #255
  beq :+
  dec _monosh_player_invuln
:
  rep #$20
  ldy #0
  lda (c_sp),y
  and #15
  sta $0342
  bne move
  lda _monosh_player_bottom
  cmp #201
  jne done
  jsr toggle_fraction
  jmp ground_pose
move:
  jsr toggle_fraction
  lda #5
  sec
  sbc $0344
  sta $0346
  stz $0348
  stz $034a
  lda $0342
  and #3
  cmp #1
  bne :+
  inc $0348
  bra vertical
:
  cmp #2
  bne vertical
  dec $0348
vertical:
  lda $0342
  and #12
  cmp #8
  bne :+
  inc $034a
  bra diagonal
:
  cmp #4
  bne diagonal
  dec $034a
diagonal:
  lda $0348
  beq move_x
  lda $034a
  beq move_x
  dec $0346
move_x:
  lda $0348
  beq move_y
  bmi left
  lda _monosh_player_x
  clc
  adc $0346
  cmp #241
  bcc save_x
  lda #240
  bra save_x
left:
  lda _monosh_player_x
  sec
  sbc $0346
  cmp #16
  bcs save_x
  lda #16
save_x:
  sta _monosh_player_x
move_y:
  lda $034a
  beq moved
  bmi up
  lda _monosh_player_bottom
  clc
  adc $0346
  cmp #202
  bcc save_y
  lda #201
  bra save_y
up:
  lda _monosh_player_bottom
  sec
  sbc $0346
  cmp #56
  bcs save_y
  lda #56
save_y:
  sta _monosh_player_bottom
moved:
  lda _monosh_player_bottom
  xba
  sta _player_fy
  lda _monosh_player_bottom
  cmp #201
  jeq ground_pose
  sec
  sbc #56
  lsr
  lsr
  lsr
  cmp #19
  bcc :+
  lda #18
:
  tay
  stz $034c
  lda _monosh_player_x
  cmp #129
  bcc folded
  inc $034c
  sta $034e
  lda #256
  sec
  sbc $034e
folded:
  sta $034e
  clc
  adc #4
  sta $0350
  sep #$20
  stz _player_run_phase
  rep #$20
  lda _monosh_player_pose
  and #$ff
  cmp #4
  bcc :+
  lda #0
:
  sta $0352
  lda $034e
  cmp #16
  beq pose3
  lda $0352
  beq from0
  cmp #1
  beq from1
  cmp #2
  beq from2
  lda _pose_x_23,y
  and #$ff
  cmp $034e
  bcc pose2
  beq pose2
  bra pose3
from0:
  lda _pose_x_01,y
  and #$ff
  cmp $0350
  bcs pose1
  bra pose0
from1:
  lda _pose_x_01,y
  and #$ff
  cmp $034e
  bcc pose0
  beq pose0
  lda _pose_x_12,y
  and #$ff
  cmp $0350
  bcs pose2
  bra pose1
from2:
  lda _pose_x_12,y
  and #$ff
  cmp $034e
  bcc pose1
  beq pose1
  lda _pose_x_23,y
  and #$ff
  cmp $0350
  bcs pose3
pose2:
  lda #2
  bra save_pose
pose1:
  lda #1
  bra save_pose
pose0:
  stz $034c
  lda #0
  bra save_pose
pose3:
  lda #3
save_pose:
  sep #$20
  sta _monosh_player_pose
  lda $034c
  sta _player_flip
  rep #$20
  bra done
ground_pose:
  lda $0344
  beq new_run_pose
  lda _monosh_player_pose
  and #$ff
  cmp #10
  bcc new_run_pose
  cmp #14
  bcc run_advance
new_run_pose:
  lda _player_run_phase
  and #$ff
  lsr
  clc
  adc #10
  sep #$20
  sta _monosh_player_pose
  rep #$20
run_advance:
  sep #$20
  lda $0344
  bne :+
  lda _player_run_phase
  inc
  and #7
  sta _player_run_phase
:
  stz _player_flip
  rep #$20
done:
  inc c_sp                  ; nativeは入力1byteだけを消費する。
  plp
  rts
toggle_fraction:
  lda _movement_fraction
  and #$ff
  eor #1
  sta $0344
  sep #$20
  sta _movement_fraction
  rep #$20
  rts
reference:
  lda $0340
  plp
  jmp _monosh_player_update_reference
.endif
