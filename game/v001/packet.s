.setcpu "65816"
.smart
.macpack longbranch
.export _fx_build_packet
.export packet_done
.import _fx_draw, _fx_draw_count, _fx_packet, _fx_packet_count
.import _fx_asset_width, _fx_asset_height, _fx_asset_bank
.import _monosh_runtime_frame_counter
.import fx_reset_next_bounds, fx_add_next_bounds
.import fx_is_obj, fx_build_obj
.segment "ZEROPAGE"
dp: .res 2
pp: .res 2
steps: .res 2
.segment "BSS"
order: .res 128
keys: .res 128
.segment "CODE"
.a8
.i8
_fx_build_packet:
  php
  rep #$30
  jsr fx_build_obj
  jsr fx_reset_next_bounds
  lda _fx_draw_count
  and #$ff
  sta $0140
  asl
  asl
  clc
  adc $0140
  asl
  sta $0142                ; total draw bytes
  lda $0140
  asl
  sta $0148                ; ソートする2byte indexの総量
  ldy #0
  ldx #0
initialize_order:
  cpx $0142
  bcs initialized
  jsr fx_is_obj
  bne omit_obj
  txa
  sta order,y
  lda _fx_draw+8,x
  eor #$00ff               ; priority昇順、同priorityならZ降順
  sta keys,y
  iny
  iny
omit_obj:
  txa
  clc
  adc #10
  tax
  bra initialize_order
initialized:
  sty $0148                ; FXへ送る分だけをソート。論理draw自体は保存。
  lda #2
  sta $0144
sort:
  lda $0144
  cmp $0148
  bcs sorted
  tay
  lda order,y
  sta $015a
  lda keys,y
  sta $0158
  dey
  dey
compare:
  lda keys,y
  cmp $0158
  bcc insert
  beq insert
  sta keys+2,y
  lda order,y
  sta order+2,y
  dey
  dey
  bpl compare
insert:
  iny
  iny
  lda $015a
  sta order,y
  lda $0158
  sta keys,y
  inc $0144
  inc $0144
  bra sort
sorted:
  lda #_fx_draw
  sta dp
  lda #_fx_packet
  sta pp
  stz _fx_packet_count
  stz $0144
next:
  lda $0144
  cmp $0148
  bcc fast_compile
packet_done:
  plp
  rts
; 四辺が画面内の通常スプライト。divider待ちはpacketの書込と重ねる。
.ifdef FX_GSU_UV
.ifdef FX_GSU_CLIP
fast_compile:
  ldy $0144
  lda order,y
  tax
  lda _fx_draw+7,x
  and #$ff
  sta $016a
  and #$80
  beq :+
  lda _monosh_runtime_frame_counter
  and #1
  jne skip
:
  lda pp
  sec
  sbc #_fx_packet
  tay
  lda _fx_draw,x
  sta _fx_packet,y
  lda _fx_draw+2,x
  sta _fx_packet+2,y
  lda _fx_draw+4,x
  sta _fx_packet+4,y
  lda _fx_draw+6,x
  sta _fx_packet+6,y
  lda _fx_draw+8,x
  sta _fx_packet+8,y
  inc _fx_packet_count
  lda pp
  clc
  adc #10
  sta pp
skip:
  inc $0144
  inc $0144
  jmp next
.else
fast_compile:
  ldy $0144
  lda order,y
  tax
  lda _fx_draw+7,x
  and #$ff
  sta $016a
  and #$80
  beq :+
  lda _monosh_runtime_frame_counter
  and #1
  jne skip
:
  lda _fx_draw+6,x
  and #$ff
  sta $0164
  lda _fx_draw+4,x
  and #$ff
  sta $0160
  sta $0178                 ; 生の幅。UV表の添字。
  lsr
  sta $0170
  lda _fx_draw,x
  sec
  sbc $0170
  sta $0172
  stz $016c
  bpl gsu_x_positive
  eor #$ffff
  inc
  sta $016c
  lda $0160
  clc
  adc $0172
  sta $0160
  stz $0172
gsu_x_positive:
  lda $0172
  clc
  adc $0160
  cmp #257
  bcc :+
  lda #256
  sec
  sbc $0172
  sta $0160
:
  lda _fx_draw+5,x
  and #$ff
  sta $0162
  sta $017a                 ; 生の高さ。
  lda _fx_draw+2,x
  sec
  sbc $0162
  sec
  sbc #20
  sta $0174
  stz $016e
  bpl gsu_y_positive
  eor #$ffff
  inc
  sta $016e
  lda $0162
  clc
  adc $0174
  sta $0162
  stz $0174
gsu_y_positive:
  lda $0174
  clc
  adc $0162
  cmp #193
  bcc :+
  lda #192
  sec
  sbc $0174
  sta $0162
:
  lda $0160
  jeq skip
  jmi skip
  lda $0162
  jeq skip
  jmi skip
  lda pp
  sec
  sbc #_fx_packet
  tay
  lda $0172
  sta _fx_packet,y
  sta _fx_packet+8,y
  lda $0174
  sta _fx_packet+2,y
  lda $0178
  sta _fx_packet+4,y
  lda $017a
  sta _fx_packet+6,y
  lda $0162
  sta _fx_packet+10,y
  lda $0164
  and #1
  beq :+
  lda #$8000
:
  ora $016e                 ; base V + 整数のskip Y
  sta _fx_packet+12,y
  lda $0160
  sta _fx_packet+14,y
  lda $016c
  sta _fx_packet+16,y
  lda $016a
  and #$30
  asl
  asl
  ora $0164                 ; 下6bitはasset、上2bitはX/Y反転
  xba
  sta $017c
  ldx $0164
  lda _fx_asset_bank,x
  and #$ff
  ora $017c
  sta _fx_packet+18,y
  jsr fx_add_next_bounds
  inc _fx_packet_count
  lda pp
  clc
  adc #20
  sta pp
skip:
  inc $0144
  inc $0144
  jmp next
.endif
.else
fast_compile:
  ldy $0144
  lda order,y
  tax
  clc
  adc #_fx_draw
  sta dp
  lda _fx_draw+4,x
  and #$ff
  sta $0160
  lsr
  sta $0170
  lda _fx_draw,x
  sec
  sbc $0170
  sta $0172
  cmp #256
  jcs compile
  clc
  adc $0160
  cmp #257
  jcs compile
  lda _fx_draw+5,x
  and #$ff
  sta $0162
  lda _fx_draw+2,x
  sec
  sbc $0162
  sec
  sbc #20
  sta $0174
  cmp #192
  jcs compile
  clc
  adc $0162
  cmp #193
  jcs compile
  lda _fx_draw+7,x
  and #$ff
  sta $016a
  and #$80
  beq :+
  lda _monosh_runtime_frame_counter
  and #1
  jne skip
:
  lda _fx_draw+6,x
  and #$ff
  sta $0164
  tax
  lda _fx_asset_width,x
  and #$ff
  xba
  sta f:$004204
  sep #$20
  lda $0160
  sta f:$004206
  rep #$20
  lda pp
  sec
  sbc #_fx_packet
  tay
  lda $0172
  sta _fx_packet,y
  sta _fx_packet+8,y
  lda $0174
  sta _fx_packet+2,y
  lda f:$004214
  sta $0166
  lda $016a
  and #$10
  beq ordinary_u
  lda $0166
  eor #$ffff
  inc
  sta _fx_packet+4,y
  lda _fx_asset_width,x
  and #$ff
  xba
  dec
  bra save_u
ordinary_u:
  lda $0166
  sta _fx_packet+4,y
  lda #0
save_u:
  sta _fx_packet+16,y
  lda _fx_asset_height,x
  and #$ff
  xba
  sta f:$004204
  sep #$20
  lda $0162
  sta f:$004206
  rep #$20
  lda $0160
  sta _fx_packet+14,y
  lda $0162
  sta _fx_packet+10,y
  lda _fx_asset_bank,x
  and #$ff
  sta _fx_packet+18,y
  lda $0164
  and #1
  beq :+
  lda #$8000
:
  sta $016e
  lda f:$004214
  sta $0168
  lda $016a
  and #$20
  beq ordinary_v
  lda $0168
  eor #$ffff
  inc
  sta _fx_packet+6,y
  lda _fx_asset_height,x
  and #$ff
  xba
  dec
  ora $016e
  bra save_v
ordinary_v:
  lda $0168
  sta _fx_packet+6,y
  lda $016e
save_v:
  sta _fx_packet+12,y
  jsr fx_add_next_bounds
  inc _fx_packet_count
  lda pp
  clc
  adc #20
  sta pp
  jmp skip
compile:
  ldy #4
  lda (dp),y
  and #$ff
  sta $0160                 ; width
  ldy #5
  lda (dp),y
  and #$ff
  sta $0162                 ; height
  ldy #6
  lda (dp),y
  and #$ff
  sta $0164                 ; asset
  tax
  lda _fx_asset_width,x
  and #$ff
  xba
  sta f:$004204
  sep #$20
  lda $0160
  sta f:$004206
  rep #$20
  .repeat 8
    nop
  .endrepeat
  lda f:$004214
  sta $0166                 ; du
  lda _fx_asset_height,x
  and #$ff
  xba
  sta f:$004204
  sep #$20
  lda $0162
  sta f:$004206
  rep #$20
  .repeat 8
    nop
  .endrepeat
  lda f:$004214
  sta $0168                 ; dv
  ldy #7
  lda (dp),y
  and #$ff
  sta $016a                 ; flags
  and #$80
  beq :+
  lda _monosh_runtime_frame_counter
  and #1
  beq :+
  jmp skip
:
  stz $016c                 ; u0
  stz $016e                 ; v0 (within asset)
  lda $0160
  lsr
  sta $0170
  ldy #0
  lda (dp),y
  sec
  sbc $0170
  sta $0172                 ; x
  bpl x_positive
  eor #$ffff
  inc
  tax
  lda $0160
  clc
  adc $0172
  sta $0160
  stz $0172
  lda #0
clip_x:
  lda $0166
  jsr clip_product
  sta $016c
x_positive:
  lda $0172
  clc
  adc $0160
  cmp #257
  bcc :+
  lda #256
  sec
  sbc $0172
  sta $0160
:
  ldy #2
  lda (dp),y
  sec
  sbc $0162
  sec
  sbc #20
  sta $0174                 ; y
  bpl y_positive
  eor #$ffff
  inc
  tax
  lda $0162
  clc
  adc $0174
  sta $0162
  stz $0174
  lda #0
clip_y:
  lda $0168
  jsr clip_product
  sta $016e
y_positive:
  lda $0174
  clc
  adc $0162
  cmp #193
  bcc :+
  lda #192
  sec
  sbc $0174
  sta $0162
:
  lda $0160
  jeq skip
  jmi skip
  lda $0162
  jeq skip
  jmi skip
  ldx $0164
  lda $016a
  and #$10
  beq :+
  lda _fx_asset_width,x
  and #$ff
  xba
  dec
  sec
  sbc $016c
  sta $016c
  lda $0166
  eor #$ffff
  inc
  sta $0166
:
  lda $016a
  and #$20
  beq :+
  lda _fx_asset_height,x
  and #$ff
  xba
  dec
  sec
  sbc $016e
  sta $016e
  lda $0168
  eor #$ffff
  inc
  sta $0168
:
  lda $0164
  and #1
  beq :+
  lda $016e
  ora #$8000
  sta $016e
:
  ldy #0
  lda $0172
  sta (pp),y
  ldy #8
  sta (pp),y
  ldy #2
  lda $0174
  sta (pp),y
  ldy #4
  lda $0166
  sta (pp),y
  ldy #6
  lda $0168
  sta (pp),y
  ldy #10
  lda $0162
  sta (pp),y
  ldy #12
  lda $016e
  sta (pp),y
  ldy #14
  lda $0160
  sta (pp),y
  ldy #16
  lda $016c
  sta (pp),y
  ldy #18
  lda _fx_asset_bank,x
  and #$ff
  sta (pp),y
  jsr fx_add_next_bounds
  inc _fx_packet_count
  lda pp
  clc
  adc #20
  sta pp
skip:
  inc $0144
  inc $0144
  jmp next
; X*duを最大8段のshift/addで作る。画面外px分の反復加算を避ける。
clip_product:
  sta $0178
  stz $0176
product_loop:
  txa
  lsr
  tax
  bcc product_shift
  lda $0176
  clc
  adc $0178
  sta $0176
product_shift:
  asl $0178
  cpx #0
  bne product_loop
  lda $0176
  rts
.endif
