.setcpu "65816"
.smart
.macpack longbranch
.ifndef FX_REFERENCE
.export _monosh_boss_render_only, _fx_boss_project
.import _boss_part_x, _boss_part_bottom, _boss_part_z, _boss_part_active, _boss_part_timer
.import _monosh_ground_screen_delta, _boss_render_camera_delta
.import _monosh_boss_bom_geometry, _monosh_boss_face_geometry, _monosh_boss_body_geometry
.import fx_emit_native
.import _boss_history_x, _boss_history_y, _boss_history_z, _history_head, _boss_age
.segment "CODE"
.a8
.i8
_monosh_boss_render_only:
  php
  rep #$30
  lda _monosh_ground_screen_delta
  and #$ff
  sec
  sbc _boss_render_camera_delta
  and #$ff
  cmp #128
  bcc :+
  ora #$ff00
:
  sta $02c2
  sep #$20
  lda _monosh_ground_screen_delta
  sta _boss_render_camera_delta
  rep #$20
  lda #8
  sta $02c0
part:
  ldx $02c0
  lda _boss_part_active,x
  and #$ff
  jeq next
  lda _boss_part_bottom,x
  and #$ff
  clc
  adc $02c2
  bpl :+
  lda #0
:
  cmp #256
  bcc :+
  lda #255
:
  sta $0244
  sep #$20
  sta _boss_part_bottom,x
  rep #$20
  lda _boss_part_x,x
  and #$ff
  sta $0242
  lda _boss_part_z,x
  and #$ff
  cmp #111
  bcc :+
  lda #110
:
  sta $024a
  asl
  tay
  lda _boss_part_active,x
  and #$ff
  cmp #2
  beq explosion
  cpx #0
  beq face
  lda _monosh_boss_body_geometry,y
  sta $0246
  lda #13
  bra emit
face:
  lda _monosh_boss_face_geometry,y
  sta $0246
  lda #14
  bra emit
explosion:
  lda _monosh_boss_bom_geometry,y
  sta $0246
  lda _boss_part_timer,x
  and #$ff
  sta $02c4
  lda #112
  sec
  sbc $02c4
  lsr
  lsr
  lsr
  tax
  lda f:$7f0000+explosion_art,x
  and #$ff
emit:
  sta $0248
  jsr fx_emit_native
next:
  dec $02c0
  jpl part
  plp
  rts
explosion_art:
  .byte 5,39,40,41,40,39,5,39,40,41,40,39,5,39,40

.a8
.i8
_fx_boss_project:
  php
  rep #$30
  stz $02c0
  stz $02c4                 ; 出現までの更新数、部位ごとに10加算
  lda _history_head
  and #$ff
  sta $02c6
  lda _monosh_ground_screen_delta
  and #$ff
  cmp #128
  bcc :+
  ora #$ff00
:
  sta $02c2
project_part:
  ldx $02c0
  lda _boss_age
  and #$ff
  cmp $02c4
  bcs project_visible
  sep #$20
  stz _boss_part_active,x
  rep #$20
  bra project_next
project_visible:
  ldy $02c6
  lda _boss_history_x,y
  sep #$20
  sta _boss_part_x,x
  lda _boss_history_z,y
  sta _boss_part_z,x
  rep #$20
  and #$ff
  asl
  tay
  cpx #0
  beq project_face
  lda _monosh_boss_body_geometry+1,y
  bra project_height
project_face:
  lda _monosh_boss_face_geometry+1,y
project_height:
  and #$ff
  lsr
  sta $02c8
  ldy $02c6
  lda _boss_history_y,y
  and #$ff
  clc
  adc $02c2
  clc
  adc $02c8
  bpl :+
  lda #0
:
  cmp #256
  bcc :+
  lda #255
:
  sep #$20
  sta _boss_part_bottom,x
  lda #1
  sta _boss_part_active,x
  rep #$20
project_next:
  lda $02c6
  sec
  sbc #10
  and #127
  sta $02c6
  lda $02c4
  clc
  adc #10
  sta $02c4
  inc $02c0
  lda $02c0
  cmp #9
  jcc project_part
  sep #$20
  lda _boss_age
  cmp #255
  beq :+
  inc _boss_age
:
  plp
  rts
.endif
