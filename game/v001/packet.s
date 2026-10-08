.setcpu "65816"
.smart
.macpack longbranch
.ifdef FX_4BPP
.include "assets4/source4.inc"
.endif
.export _fx_build_packet
.export packet_done
.export initialized, sorted
.import _fx_draw, _fx_draw_count, _fx_packet, _fx_packet_count
.import _fx_asset_width, _fx_asset_height, _fx_asset_bank
.import _monosh_runtime_frame_counter
.import fx_reset_next_bounds, fx_add_next_bounds
.import fx_is_obj, fx_build_obj
.ifndef FX_4BPP
.import fx_build_color
.endif
.export order, packet_work
.segment "ZEROPAGE"
dp: .res 2
pp: .res 2
steps: .res 2
packet_work: .res 32 ; ??????????routine????scratch?DP????
.segment "BSS"
order: .res 128
keys: .res 128
.ifdef FX_BUCKET_SORT
bucket_heads: .res 512
bucket_links: .res 128
.export bucket_heads, bucket_links, keys
.endif
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
  sta packet_work+0
  asl
  asl
  clc
  adc packet_work+0
  asl
  sta packet_work+2                ; total draw bytes
  lda packet_work+0
  asl
  sta packet_work+8                ; ソートする2byte indexの総量
  ldy #0
  ldx #0
.ifdef FX_BUCKET_SORT
  stz $0162                ; priorityが混在する時は元の安定insertion sort。
.endif
initialize_order:
  cpx packet_work+2
  bcs initialized
  jsr fx_is_obj
  bne omit_obj
  txa
  sta order,y
  lda _fx_draw+8,x
  eor #$00ff               ; priority昇順、同priorityならZ降順
  sta keys,y
.ifdef FX_BUCKET_SORT
  jsr bucket_record
.endif
  iny
  iny
omit_obj:
  txa
  clc
  adc #10
  tax
  bra initialize_order
initialized:
  sty packet_work+8                ; FXへ送る分だけをソート。論理draw自体は保存。
.ifdef FX_BUCKET_SORT
  cpy #24                  ; 12体以上で比較・移動の二乗費用を避ける。
  bcc insertion_sort
  lda $0162
  bne insertion_sort
  lda $0166
  sec
  sbc $0164
  cmp #129                 ; 広く散った少数commandはinsertionの方が安い。
  bcs insertion_sort
  jmp bucket_sort
insertion_sort:
.endif
  lda #2
  sta packet_work+4
sort:
  lda packet_work+4
  cmp packet_work+8
  bcs sorted
  tay
  lda order,y
  sta packet_work+26
  lda keys,y
  sta packet_work+24
  dey
  dey
compare:
  lda keys,y
  cmp packet_work+24
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
  lda packet_work+26
  sta order,y
  lda packet_work+24
  sta keys,y
  inc packet_work+4
  inc packet_work+4
  bra sort
sorted:
  lda #_fx_draw
  sta dp
  lda #_fx_packet
  sta pp
  stz _fx_packet_count
  stz packet_work+4
next:
  lda packet_work+4
  cmp packet_work+8
  bcc fast_compile
packet_done:
  .ifndef FX_4BPP
  jsr fx_build_color
  .endif
  plp
  rts
; 四辺が画面内の通常スプライト。divider待ちはpacketの書込と重ねる。
.ifdef FX_GSU_UV
.ifdef FX_GSU_CLIP
fast_compile:
  ldy packet_work+4
  lda order,y
  tax
  lda _fx_draw+7,x
  and #$ff
  sta $016a
  and #$80
  beq :+
  lda _monosh_runtime_frame_counter
  .ifdef FX_4BPP
  lsr                       ; 2 tickごとの描画でも点滅が片側に固定されない。
  .endif
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
  .ifdef FX_4BPP
  .if FX4_COLOR
  and #$ff
  cmp #10
  bne color_bullet_done
  lda _fx_draw+4,x
  and #$ff
  lsr
  sta $0170
  lda _fx_draw+7,x
  and #$40
  beq :+
  lda #14                  ; 反射弾はsize7の12x8。
  bra color_bullet_size
:
  lda _fx_draw+4,x
  and #$ff
  asl
color_bullet_size:
  phx
  tax
  lda color_bullet_dimensions,x
  plx
  sta _fx_packet+4,y
  xba
  and #$ff
  lsr
  clc
  adc _fx_draw+2,x
  sec
  sbc $0170
  sta _fx_packet+2,y
color_bullet_done:
  .endif
  .endif
  .ifndef FX_CPU_CLIP_COMMANDS
  lda _fx_draw+8,x
  sta _fx_packet+8,y
  .endif
  .ifdef FX_CPU_CLIP_COMMANDS
  ; 転送packetの末尾wordだけを制御値にする。元FxDraw・ソートキーは保存。
  ; $8000=INSIDE、0=GSUでclip。FB座標はleft=center-width/2、top=bottom-height-20。
  lda #0
  sta _fx_packet+8,y
  lda _fx_draw+4,x
  and #$ff
  beq command_classified
  sta $0160
  lsr
  sta $0170
  lda _fx_draw,x
  sec
  sbc $0170
  cmp #256
  bcs command_classified
  clc
  adc $0160
  cmp #257
  bcs command_classified
  lda _fx_draw+2,x
  sec
  sbc #20
  cmp #193                 ; bottom-20 <=192、負数もunsigned比較で除外。
  bcs command_classified
  sta $0162
  lda _fx_draw+5,x
  and #$ff
  beq command_classified
  sta $0170
  lda $0162
  sec
  sbc $0170
  cmp #192
  bcs command_classified
  lda #$8000
  sta _fx_packet+8,y
command_classified:
  .endif
  inc _fx_packet_count
  lda pp
  clc
  adc #10
  sta pp
skip:
  inc packet_work+4
  inc packet_work+4
  jmp next
.else
fast_compile:
  ldy packet_work+4
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
  inc packet_work+4
  inc packet_work+4
  jmp next
.endif
.else
fast_compile:
  ldy packet_work+4
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
  inc packet_work+4
  inc packet_work+4
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

.ifdef FX_BUCKET_SORT
.include "packet_bucket.inc"
.endif
.ifdef FX_4BPP
.segment "RODATA"
color_bullet_dimensions:
  .word $0000,$0101,$0202,$0404,$0406,$0608,$060a,$080c,$0c10
  .word $1018,$1420,$1828,$2038,$2038,$2038,$2038,$2038
.endif
