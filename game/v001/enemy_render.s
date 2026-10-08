.setcpu "65816"
.smart
.macpack longbranch
.ifdef FX_4BPP
.include "assets4/source4.inc"
.if FX4_COLOR
.import _monosh_runtime_frame_counter
.endif
.endif
.export _fx_enemy_render, _fx_enemy_render_bullets
.export fx_emit_native
.import _monosh_enemies, _monosh_enemy_active_count_value
.import _monosh_enemy_bullets, _monosh_enemy_bullet_count
.import _monosh_em1_closed_geometry, _monosh_em1_open_geometry
.import _monosh_ebullet_geometry, _monosh_ebullet_animation_geometry
.import _monosh_ground_screen_delta, _fx_draw, _fx_draw_count
.ifdef FX_SMOOTH_DEPTH
.import fx_em1_open_sizes
.endif
.segment "ZEROPAGE"
er: .res 2
eg: .res 2
.segment "CODE"
.a8
.i8
; C版の後ろからの走査順・整数丸め・粗い画面外判定を維持する。
_fx_enemy_render:
  php
  rep #$30
  lda _monosh_enemy_active_count_value
  and #$ff
  sta $0240
  asl
  sta $024c
  asl
  asl
  clc
  adc $024c
  adc #_monosh_enemies
  sta er
enemy_loop:
  lda $0240
  jeq render_done
  lda er
  sec
  sbc #10
  sta er
  ldy #4
  lda (er),y
  and #$ff
  sec
  sbc #64
  asl
  sta $0242
  ldy #5
  lda (er),y
  and #$ff
  sta $0244
  ldy #6
  lda (er),y
  and #$ff
  cmp #111
  bcc :+
  lda #110
:
  sta $024a
  ldy #1
  lda (er),y
  and #$ff
  cmp #6
  beq em1
  cmp #2
  beq bom
  lda #3
  bra cached
bom:
  ldy #3
  lda (er),y
  and #$ff
  sta $024c
  lda #48
  sec
  sbc $024c
  and #$ff
  lsr
  lsr
  lsr
  cmp #4
  bcc :+
  sta $024c
  lda #6
  sec
  sbc $024c
:
  cmp #0
  beq bom_default
  clc
  adc #38
  bra cached
bom_default:
  lda #5
cached:
  sta $0248
  ldy #8
  lda (er),y
  sta $0246
  bra enemy_emit
em1:
  lda _monosh_ground_screen_delta
  and #$ff
  cmp #$80
  bcc :+
  ora #$ff00
:
  clc
  adc $0244
  sta $0244
  ldy #7
  lda (er),y
  and #7
  bne em1_open
  lda #11
  sta $0248
  lda $024a
  asl
  tax
  lda _monosh_em1_closed_geometry,x
  bra em1_geometry
em1_open:
  sta $024c
  clc
  adc #31
  sta $0248
  lda $024a
  .ifdef FX_SMOOTH_DEPTH
  ; Z*10+(pose-1)*2。5pose×111項目をWRAM7Fから直接読む。
  asl
  sta $024e
  asl
  asl
  clc
  adc $024e
  sta $024e
  lda $024c
  dec
  asl
  clc
  adc $024e
  tax
  lda f:$7f0000+fx_em1_open_sizes,x
  .else
  ldx #0
  cmp #80
  bcs :+
  ldx #5
  cmp #54
  bcs :+
  ldx #10
:
  txa
  clc
  adc $024c
  dec
  asl
  tax
  lda _monosh_em1_open_geometry,x
  .endif
em1_geometry:
  sta $0246
enemy_emit:
  jsr emit
  dec $0240
  jmp enemy_loop
render_done:
  plp
  rts

_fx_enemy_render_bullets:
  php
  rep #$30
  lda _monosh_enemy_bullet_count
  and #$ff
  sta $0240
  sta $024c
  asl
  asl
  asl
  sec
  sbc $024c
  clc
  adc #_monosh_enemy_bullets
  sta er
bullet_loop:
  lda $0240
  jeq render_done
  lda er
  sec
  sbc #7
  sta er
  ldy #1
  lda (er),y
  and #$ff
  sec
  sbc #64
  asl
  sta $0242
  ldy #2
  lda (er),y
  and #$ff
  sta $0244
  ldy #3
  lda (er),y
  and #$ff
  cmp #111
  bcc :+
  lda #110
:
  sta $024a
  ldy #6
  lda (er),y
  and #$ff
  bit #$80
  beq bullet_normal
  .ifdef FX_4BPP
  .if FX4_COLOR
  lda _monosh_runtime_frame_counter
  jsr bullet_hue4
  lda $0250
  ora #31
  .else
  lda #31
  .endif
  .else
  lda #31
  .endif
  sta $0248
  lda _monosh_ebullet_geometry+8
  sta eg
  bra bullet_geometry
bullet_normal:
  .ifdef FX_4BPP
  .if FX4_COLOR
  ; 回転とは独立した32 tickの色周期。紫16、赤8、青8。
  pha
  jsr bullet_hue4
  pla
  .endif
  .endif
  lsr
  lsr
  and #15
  sta $024c
  ldx #0
  cmp #4
  bcc bullet_a
  ldx #$2000
  cmp #8
  bcc bullet_b
  ldx #$3000
  cmp #12
  bcc bullet_c
  ldx #$1000
  lda #21
  bra bullet_subtract
bullet_b:
  lda #13
bullet_subtract:
  sec
  sbc $024c
  bra bullet_asset
bullet_c:
  sec
  sbc #2
  bra bullet_asset
bullet_a:
  clc
  adc #6
bullet_asset:
  cmp #9
  bne :+
  lda #37
:
  sta $0248
  txa
  ora $0248
  .ifdef FX_4BPP
  .if FX4_COLOR
  ora $0250
  .endif
  .endif
  sta $0248
  lda #_monosh_ebullet_animation_geometry
  sta eg
bullet_geometry:
  lda $024a
  asl
  tay
  lda (eg),y
  sta $0246
  jsr emit
  dec $0240
  jmp bullet_loop

  .ifdef FX_4BPP
  .if FX4_COLOR
bullet_hue4:
  and #31
  ldx #0
  cmp #16
  bcc :+
  ldx #$0200
  cmp #24
  bcc :+
  ldx #$0100
:
  stx $0250
  rts
  .endif
  .endif

; 引数は専用WRAM scratch。Cのsoftware stackへの9byte pushを省く。
emit:
fx_emit_native:
  lda $0246
  and #$ff
  jeq emit_done
  lsr
  sta $024e
  clc
  adc $0242
  jmi emit_done
  lda $0242
  sec
  sbc $024e
  cmp #256
  jpl emit_done
  lda $0246
  xba
  and #$ff
  jeq emit_done
  sta $024e
  lda $0244
  cmp #21
  jmi emit_done
  sec
  sbc $024e
  cmp #212
  jpl emit_done
  lda _fx_draw_count
  and #$ff
  cmp #64
  bcs emit_done
  asl
  sta $024e
  asl
  asl
  clc
  adc $024e
  tax
  lda $0242
  sta _fx_draw,x
  lda $0244
  sta _fx_draw+2,x
  lda $0246
  sta _fx_draw+4,x
  lda $0248
  sta _fx_draw+6,x
  lda $024a
  sta _fx_draw+8,x
  sep #$20
  inc _fx_draw_count
  rep #$20
emit_done:
  rts
