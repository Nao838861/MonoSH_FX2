.setcpu "65816"
.smart
.macpack longbranch
.export _fx_stage_update, stage_update_done
.import _monosh_stage_objects, _monosh_stage_object_count, _monosh_stage_spawn_index
.import _monosh_stage_frame_counter, _monosh_stage_half_frame, _monosh_stage_near_count
.import _monosh_stage1_spawns, _monosh_stage1_spawn_count, _monosh_player_x
.segment "CODE"
.a8
.i8
_fx_stage_update:
  php
  rep #$30
  sep #$20
  stz _monosh_stage_near_count
  lda _monosh_stage_half_frame
  eor #1
  sta _monosh_stage_half_frame
  rep #$20
  lda _monosh_player_x
  sec
  sbc #128
  .repeat 4
    cmp #$8000
    ror
  .endrepeat
  stz $0202
  bpl positive
  inc $0202
  eor #$ffff
  inc
positive:
  lsr
  bcc half_done
  pha
  lda _monosh_stage_half_frame
  and #$ff
  beq :+
  pla
  inc
  bra half_done
:
  pla
half_done:
  ldx $0202
  beq :+
  eor #$ffff
  inc
:
  sta $0200
  inc _monosh_stage_frame_counter
spawn:
  lda _monosh_stage_spawn_index
  and #$ff
  cmp _monosh_stage1_spawn_count
  jcs begin_update
  sta $0208
  asl
  clc
  adc $0208
  asl
  tay
  lda _monosh_stage1_spawns,y
  cmp _monosh_stage_frame_counter
  bcc due
  jeq due
  jmp begin_update
due:
  lda _monosh_stage1_spawns+2,y
  and #$ff
  cmp #255
  jeq begin_update
  xba
  ora #110
  sta $0206
  lda _monosh_stage_object_count
  and #$ff
  cmp #16
  bcs skip_spawn
  sta $0208
  asl
  clc
  adc $0208
  asl
  tax
  lda _monosh_stage1_spawns+3,y
  sta _monosh_stage_objects,x
  lda $0206
  sta _monosh_stage_objects+2,x
  lda _monosh_stage1_spawns+5,y
  and #$ff
  sta _monosh_stage_objects+4,x
  sep #$20
  inc _monosh_stage_object_count
  rep #$20
skip_spawn:
  sep #$20
  inc _monosh_stage_spawn_index
  rep #$20
  jmp spawn
begin_update:
  lda _monosh_stage_object_count
  and #$ff
  sta $0208
  asl
  clc
  adc $0208
  asl
  sta $0204
  ldx #0
object:
  cpx $0204
  jcs stage_update_done
  lda _monosh_stage_objects+3,x
  and #$ff
  cmp #2
  bne advance
  sep #$20
  lda _monosh_stage_objects+5,x
  beq remove
  dec _monosh_stage_objects+5,x
  lda _monosh_stage_objects+4,x
  beq :+
  dec _monosh_stage_objects+4,x
:
  lda _monosh_stage_objects+2,x
  cmp #3
  bcc remove
  rep #$20
advance:
  sep #$20
  lda _monosh_stage_objects+2,x
  beq remove
  dec _monosh_stage_objects+2,x
  bne :+
  lda #1
  sta _monosh_stage_near_count
:
  rep #$20
  lda _monosh_stage_objects,x
  sec
  sbc $0200
  sta _monosh_stage_objects,x
  txa
  clc
  adc #6
  tax
  jmp object
remove:
  rep #$20
  lda $0204
  sec
  sbc #6
  sta $0204
  tay
  .repeat 3,I
    lda _monosh_stage_objects+I*2,y
    sta _monosh_stage_objects+I*2,x
  .endrepeat
  sep #$20
  dec _monosh_stage_object_count
  rep #$20
  jmp object
stage_update_done:
  plp
  rts
