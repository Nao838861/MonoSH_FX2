.setcpu "65816"
.smart
.macpack longbranch
.export _fx_enemy_collisions
.import _monosh_enemies, _monosh_enemy_active_count_value, _monosh_enemy_em1_count
.import _monosh_player_bullets, _monosh_player_bullet_count
.import _monosh_em1_closed_geometry, _monosh_em1_open_geometry, _monosh_bom_geometry
.ifdef FX_SMOOTH_DEPTH
.import fx_em1_open_sizes
.endif
.import _monosh_ground_screen_delta, _monosh_combat_reflect_bullet
.segment "ZEROPAGE"
ce: .res 2
.segment "CODE"
.a8
.i8
_fx_enemy_collisions:
  php
  rep #$30
  lda #_monosh_enemies
  sta ce
  stz $0262
enemy:
  lda _monosh_enemy_active_count_value
  and #$ff
  cmp $0262
  jeq done
  ldy #1
  lda (ce),y
  and #$ff
  cmp #5
  beq eligible
  cmp #6
  jne next_enemy
eligible:
  sta $0270
  ldy #4
  lda (ce),y
  and #$ff
  cmp #64
  jcc next_enemy
  cmp #192
  jcs next_enemy
  sec
  sbc #64
  asl
  sta $0266
  ldy #5
  lda (ce),y
  and #$ff
  sta $0268
  stz $0264
  lda $0270
  cmp #6
  beq em1
  ldy #8
  lda (ce),y
  bra geometry
em1:
  lda _monosh_ground_screen_delta
  and #$ff
  cmp #$80
  bcc :+
  ora #$ff00
:
  clc
  adc $0268
  sta $0268
  ldy #7
  lda (ce),y
  and #$80
  bne :+
  inc $0264
:
  lda (ce),y
  and #7
  bne open
  ldy #6
  lda (ce),y
  and #$ff
  cmp #111
  bcc :+
  lda #110
:
  asl
  tax
  lda _monosh_em1_closed_geometry,x
  bra geometry
open:
  sta $0272
  ldy #6
  lda (ce),y
  and #$ff
  .ifdef FX_SMOOTH_DEPTH
  ; 描画と同じZ*10+(pose-1)*2。旧3段階の当たり判定を残さない。
  cmp #111
  bcc :+
  lda #110
:
  asl
  sta $0274
  asl
  asl
  clc
  adc $0274
  sta $0274
  lda $0272
  dec
  asl
  clc
  adc $0274
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
  adc $0272
  dec
  asl
  tax
  lda _monosh_em1_open_geometry,x
  .endif
geometry:
  pha
  and #$ff
  lsr
  sta $026a
  pla
  xba
  and #$ff
  sta $026c
  lda $0264
  beq bounds
  lda $026a
  cmp #20
  bcs :+
  lda #20
  sta $026a
:
  lda $026c
  cmp #24
  bcs bounds
  lda #24
  sta $026c
bounds:
  lda $0268
  sec
  sbc $026c
  jmi next_enemy
  sta $0274
  stz $026e
  ldx #0
bullet:
  lda _monosh_player_bullets,x
  and #$ff
  cmp #1
  jne next_bullet
  lda _monosh_player_bullets+3,x
  and #$ff
  asl
  sta $0276
  ldy #6
  lda (ce),y
  and #$ff
  sec
  sbc $0276
  ldy $0264
  beq normal_z
  clc
  adc #20
  cmp #34
  jcs next_bullet
  bra test_x
normal_z:
  clc
  adc #8
  cmp #10
  jcs next_bullet
test_x:
  lda _monosh_player_bullets+1,x
  and #$ff
  sec
  sbc $0266
  bpl :+
  eor #$ffff
  inc
:
  cmp $026a
  bcc test_y
  bne next_bullet
test_y:
  lda _monosh_player_bullets+2,x
  and #$ff
  cmp $0274
  bcc next_bullet
  cmp $0268
  bcc hit
  bne next_bullet
hit:
  lda $0264
  beq destroy
  lda $0262
  sep #$30
  tax
  lda $026e
  jsr _monosh_combat_reflect_bullet
  rep #$30
  jmp next_enemy
destroy:
  sep #$20
  stz _monosh_player_bullets,x
  dec _monosh_player_bullet_count
  lda $0270
  cmp #6
  bne :+
  dec _monosh_enemy_em1_count
:
  ldy #1
  lda #2
  sta (ce),y
  ldy #3
  lda #48
  sta (ce),y
  ldy #5
  lda $0268
  sta (ce),y
  ldy #7
  lda #12
  sta (ce),y
  rep #$20
  ldy #6
  lda (ce),y
  and #$ff
  asl
  tax
  lda _monosh_bom_geometry,x
  ldy #8
  sta (ce),y
  bra next_enemy
next_bullet:
  txa
  clc
  adc #5
  tax
  inc $026e
  lda $026e
  cmp #3
  jne bullet
next_enemy:
  lda ce
  clc
  adc #10
  sta ce
  inc $0262
  jmp enemy
done:
  plp
  rts
