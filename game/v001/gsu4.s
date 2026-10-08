.include "casfx.inc"
.include "assets4/source4.inc"
; 4bpp実験専用。ゲームのpacket/clip/UV規則は60fps版と共用する。
.segment "GSU"
.export render_entry, render_stop, background_done, dispatch_nonzero, generic, margin_render, scaled_render4, integer_render4
.export scaled_unpacked4
.align 16
render_entry:
  cache
  sub r0
  cmode
  .include "gsu_clear4.inc"
  iwt r11,#$1000
  ibt r10,#2
background_layer:
  cache                   ; 二層共通の境界計算と画素loopを同じwindowへ置く。
  ldw (r11)
  move r5,r0               ; horizontal source position (0..511)
  iwt r8,#$1010
  ldw (r8)
  add r5
  iwt r8,#511
  and r8
  move r5,r0
  inc r11
  inc r11
  ldw (r11)
  move r2,r0
  inc r11
  inc r11
  ldw (r11)
  move r6,r0
  inc r11
  inc r11
  ldw (r11)
  move r7,r0               ; ROM row address
  inc r11
  inc r11
  ibt r8,#0
  from r6
  cmp r8
  bne background_has_rows4
  nop
  iwt r8,#.loword(background_end)
  jmp (r8)
  nop
background_has_rows4:
  iwt r8,#192
  from r2
  cmp r8
  blt background_on_screen4
  nop
  iwt r8,#.loword(background_end)
  jmp (r8)
  nop
background_on_screen4:
  ibt r0,#$5f
  romb
  from r2
  lsr
  lsr
  lsr
  move r3,r0
  from r2
  add r6
  dec r0
  lsr
  lsr
  lsr
  move r4,r0
  iwt r8,#$1010
  ldw (r8)
  lsr
  lsr
  iwt r8,#$0580
  add r8
  move r8,r0
  ibt r9,#8
background_bounds:
  ldb (r8)
  cmp r3
  blt background_min_ready
  nop
  from r3
  stb (r8)
background_min_ready:
  inc r8
  ldb (r8)
  cmp r4
  bge background_max_ready
  nop
  from r4
  stb (r8)
background_max_ready:
  inc r8
  dec r9
  bne background_bounds
  nop
  iwt r0,#512
  sub r5
  move r3,r0               ; length before horizontal wrap
  iwt r0,#64
  cmp r3
  bge background_first_count
  nop
  move r3,r0
background_first_count:
  iwt r8,#64
  from r8
  sub r3
  move r4,r0               ; length after horizontal wrap
  .align 16,$01
background_cache:
background_row:
  iwt r0,#192
  from r2
  cmp r0
  bge background_end
  nop
  iwt r8,#$1010
  to r1
  ldw (r8)
  from r7
  to r14
  add r5
  move r12,r3
  iwt r13,#.loword(background_pixels)
background_pixels:
  getc
  inc r14
  loop
  plot
  ibt r0,#0
  from r4
  cmp r0
  beq background_next_row
  nop
  move r14,r7
  move r12,r4
  iwt r13,#.loword(background_tail)
background_tail:
  getc
  inc r14
  loop
  plot
background_next_row:
  iwt r0,#512
  with r7
  add r0
  inc r2
  dec r6
  bne background_row
  nop
background_end:
  rpix
  dec r10
  beq background_done
  nop
  iwt r8,#.loword(background_layer)
  jmp (r8)
  nop
background_done:
  iwt r11,#0
  ldw (r11)
  iwt r8,#4
  stw (r8)
  iwt r8,#6
  ibt r0,#32
  stw (r8)
dispatch:
  iwt r11,#4
  ldw (r11)
  ibt r8,#0
  cmp r8
  bne dispatch_nonzero
  nop
  iwt r11,#.loword(finished)
  jmp (r11)
  nop
dispatch_nonzero:
  dec r0
  stw (r11)
  iwt r11,#6
  ldw (r11)
  move r11,r0
  .include "gsu_draw.inc"
  iwt r8,#6
  from r11
  stw (r8)
  ; 43は透明の詰め物。STAGEの左端の透明画素 $59:0600 を共有する。
  from r13
  ibt r8,#63
  and r8
  ibt r8,#43
  cmp r8
  bne :+
  nop
  iwt r7,#$0600
:
  move r0,r12
  .if FX4_COLOR
  sms ($000a),r0
  ; 生packetのflags下位2bitを弾の色相として保存。UVのflip metaには混ぜない。
  move r8,r11
  dec r8
  dec r8
  dec r8
  ldb (r8)
  ibt r8,#3
  and r8
  add r0
  sms ($0016),r0
  ; 共通15色の番号には規則性を持たせない。色周期ごとの原画bank/base行を選ぶ。
  lms r0,($000a)
  swap
  ibt r8,#63
  and r8
  move r12,r0
  add r0
  add r12
  add r0
  add r0                  ; asset*12
  move r12,r0
  lms r0,($0016)
  add r0                  ; hue*4
  add r12
  move r12,r0
  ibt r0,#$5f
  romb
  iwt r8,#$6000
  from r12
  to r14
  add r8
  getb
  move r12,r0             ; bank
  inc r14
  inc r14
  getb
  inc r14
  getbh
  move r7,r0              ; base V (256byte aligned)
  sms ($000c),r0          ; 縮小行は原画内の行番号を使う。
  lms r0,($000a)
  iwt r8,#$ff00
  and r8
  or r12
  sms ($000a),r0
  .endif
  sms ($001a),r3
  sms ($001e),r4           ; 原寸height。縮小済みの縦サンプルがある組だけ使う。
  .if !FX4_COLOR
  sms ($000a),r0
  .endif
  iwt r8,#$1010
  ldw (r8)
  move r8,r0
  with r1
  sub r8
  lms r0,($000a)
  .include "gsu_clip4.inc"
  ; 縮小済みの胴・顔は水平UVを使わない。通常向きだけ先に選ぶ。
  swap
  iwt r8,#255
  and r8
  ibt r8,#13
  cmp r8
  beq prescaled_pre4
  nop
  ibt r8,#14
  cmp r8
  bne uv_normal4
  nop
prescaled_pre4:
  sms ($0010),r6
  sms ($0012),r7
  sms ($0014),r4
  ibt r0,#1
  sms ($000e),r0
  iwt r11,#.loword(scaled_select4)
  jmp (r11)
  nop
uv_normal4:
  ibt r0,#0
  sms ($000e),r0
  lms r0,($000a)
  .include "gsu_uv.inc"
  .if FX4_COLOR
  lms r0,($000a)
  swap
  ibt r8,#63
  and r8
  ibt r8,#6
  cmp r8
  blt :+
  nop
  ibt r8,#9
  cmp r8
  blt bullet_selected4
  nop
  ibt r8,#37
  cmp r8
  beq bullet_selected4
  nop
  ibt r8,#31
  cmp r8
  bne :+
  nop
  iwt r11,#.loword(scaled_select4)
  jmp (r11)
  nop
bullet_selected4:
  iwt r11,#.loword(bullet_render4)
  jmp (r11)
  nop
:
  .endif
  ibt r8,#$ff
  from r3
  and r8
  bne :+
  nop
  iwt r11,#.loword(integer_render4)
  jmp (r11)
  nop
:
  iwt r11,#.loword(scaled_select4)
  jmp (r11)
  nop
margin_select4:
  ibt r8,#0
  from r3
  cmp r8
  blt generic_jump
  nop
  iwt r8,#$001a
  ldw (r8)
  ibt r8,#32
  cmp r8
  blt generic_jump
  nop
  ibt r0,#$5e
  romb
  lms r0,($000a)
  swap
  ibt r8,#63
  and r8
  iwt r8,#$b058
  to r14
  add r8
  getb
  iwt r8,#255
  cmp r8
  beq margin_reject
  nop
  swap
  move r12,r0
  add r0
  add r12
  iwt r8,#$b100
  add r8
  move r12,r0
  lms r0,($001a)
  move r8,r0
  add r0
  add r8
  to r14
  add r12
  getb
  sms ($001c),r0
  inc r14
  getb
  inc r14
  getbh
  move r11,r0
  iwt r8,#.loword(margin_render)
  jmp (r8)
  nop
margin_reject:
  lms r0,($000a)
  romb
generic_jump:
  lms r0,($000a)
  romb
  iwt r11,#.loword(generic)
  jmp (r11)
  nop
.align 16,$01
generic:
  cache
  .include "gsu_generic_pipeline.inc"
  .if FX4_COLOR
.align 16,$01
.export bullet_render4
bullet_render4:
  ; 原画選択済み。通常のGETC経路なので1画素ごとの色相演算は不要。
  lms r0,($000a)
  romb
  iwt r11,#.loword(generic)
  jmp (r11)
  nop
  .endif
.align 16,$01
margin_render:
  cache
  iwt r13,#.loword(margin_pixel)
margin_row:
  lms r0,($001c)
  romb
  from r7
  swap
  ibt r8,#127
  and r8
  to r14
  add r11
  move r1,r5
  getb
  iwt r8,#255
  cmp r8
  beq margin_next_row
  nop
  move r10,r0
  lms r0,($001a)
  sub r10
  move r12,r0
  lms r0,($000a)
  romb
  lms r0,($0018)
  cmp r10
  blt margin_left_ready
  nop
  move r10,r0
margin_left_ready:
  from r10
  umult r3
  move r8,r0
  from r3
  swap
  umult r10
  swap
  with r8
  add r0
  lms r0,($0018)
  add r9
  cmp r12
  bge margin_right_ready
  nop
  move r12,r0
margin_right_ready:
  from r12
  sub r10
  beq margin_next_row
  nop
  blt margin_next_row
  nop
  move r12,r0
  merge r14
  with r8
  add r3
  lms r0,($0018)
  from r10
  sub r0
  with r1
  add r0
  getc
margin_pixel:
  merge r14
  with r8
  add r3
  plot
  loop
  getc
margin_next_row:
  with r7
  add r4
  dec r6
  bne margin_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
finished:
  rpix
  iwt r11,#0
  ldw (r11)
  iwt r11,#$1012
  ldw (r11)
  ibt r8,#0
  cmp r8
  bne render_plan
  nop
  ibt r0,#1
  stw (r11)
  iwt r11,#$1010
  ldw (r11)
  iwt r8,#128
  add r8
  stw (r11)
  iwt r11,#.loword(render_entry)
  jmp (r11)
  nop
render_plan:
  iwt r11,#.loword(plan_dma4)
  jmp (r11)
  nop
render_stop:
  stop
  nop

; ボス胴・顔・爆発4姿勢・ボス弾を同じQ8.8で水平縮小済み。通常の向きだけを使用する。
scaled_select4:
  lms r0,($000a)
  swap
  iwt r8,#192
  and r8
  beq :+
  nop
  iwt r11,#.loword(scaled_reject4)
  jmp (r11)
  nop
:
  lms r0,($000a)
  swap
  ibt r8,#63
  and r8
  ibt r8,#13
  cmp r8
  beq scaled_body4
  nop
  ibt r8,#14
  cmp r8
  beq scaled_face4
  nop
  ibt r8,#5
  cmp r8
  beq scaled_bom4
  nop
  ibt r8,#39
  cmp r8
  beq scaled_bom39
  nop
  ibt r8,#40
  cmp r8
  beq scaled_bom40
  nop
  ibt r8,#41
  cmp r8
  beq scaled_bom41
  nop
  ibt r8,#31
  cmp r8
  beq scaled_bullet4
  nop
  iwt r11,#.loword(scaled_reject4)
  jmp (r11)
  nop
scaled_bullet4:
  iwt r12,#$3800
  .if FX4_COLOR
  lms r0,($0016)
  swap
  add r0
  to r12
  add r12
  .endif
  bra scaled_lookup4
  nop
scaled_bom41:
  nop
  iwt r12,#$3400
  bra scaled_lookup4
  nop
scaled_body4:
  iwt r12,#$2000
  bra scaled_lookup4
  nop
scaled_face4:
  iwt r12,#$2400
  bra scaled_lookup4
  nop
scaled_bom4:
  iwt r12,#$2800
  bra scaled_lookup4
  nop
scaled_bom39:
  iwt r12,#$2c00
  bra scaled_lookup4
  nop
scaled_bom40:
  iwt r12,#$3000
scaled_lookup4:
  ibt r0,#$5f
  romb
  from r12
  lsr
  .if FX4_COLOR
  iwt r8,#$3800
  .else
  iwt r8,#$2c00
  .endif
  add r8
  move r14,r0
  lms r0,($001a)
  add r0
  to r14
  add r14
  getb
  lms r8,($001e)
  from r8
  cmp r0
  bge :+
  inc r14
  iwt r11,#.loword(scaled_reject4)
  jmp (r11)
  nop
:
  getb
  cmp r8
  bge :+
  nop
  iwt r11,#.loword(scaled_reject4)
  jmp (r11)
  nop
:
scaled_height_valid4:
  lms r0,($001a)
  add r0
  add r0
  to r14
  add r12
  getb
  inc r14
  getbh
  move r12,r0
  inc r14
  getb
  inc r14
  getbh
  move r10,r0
  move r0,r12
  ibt r8,#0
  cmp r8
  beq scaled_reject4
  nop
  lms r0,($000e)
  cmp r8
  beq scaled_uv_ready4
  nop
  ; 先行選択に成功した場合は、垂直UVだけを元と同じ整数式で作る。
  ibt r0,#$5e
  romb                    ; R14更新より先にbankを選び、先読みを新bankへ向ける。
  lms r0,($000a)
  swap
  ibt r8,#63
  and r8
  swap
  add r0
  move r11,r0
  lms r0,($0014)
  add r0
  add r11
  iwt r8,#$5800
  to r14
  add r8
  getb
  inc r14
  getbh
  move r6,r0
  iwt r8,#255
  from r7
  and r8
  lmult
  move r7,r4
  move r4,r6
  lms r6,($0010)
scaled_uv_ready4:
  .if FX4_COLOR
  lms r0,($000e)
  ibt r8,#0
  cmp r8
  bne :+
  nop
  lms r0,($000c)
  with r7
  sub r0
:
  .endif
  move r0,r12             ; ROMBの後のSWAPにもbank/形式の値を残す。
  romb
  swap
  iwt r8,#255
  and r8
  move r3,r0
  ibt r8,#0
  cmp r8
  beq scaled_packed_select4
  nop
  iwt r11,#.loword(scaled_unpacked4)
  jmp (r11)
  nop
scaled_packed_select4:
  iwt r11,#.loword(scaled_render4)
  jmp (r11)
  nop
scaled_reject4:
  lms r0,($000e)
  ibt r8,#0
  cmp r8
  beq scaled_generic_reject4
  nop
  lms r3,($001a)
  lms r4,($0014)
  lms r6,($0010)
  lms r7,($0012)
  lms r10,($0018)
  iwt r11,#.loword(uv_normal4)
  jmp (r11)
  nop
scaled_generic_reject4:
  .if FX4_COLOR
  lms r0,($000a)
  swap
  ibt r8,#63
  and r8
  ibt r8,#31
  cmp r8
  bne :+
  nop
  lms r0,($000a)
  romb                    ; 縮小表を参照した5Fから原画bankへ戻す。
  iwt r11,#.loword(bullet_render4)
  jmp (r11)
  nop
:
  .endif
  iwt r11,#.loword(margin_select4)
  jmp (r11)
  nop

.align 16,$01
scaled_render4:
  cache
scaled_row4:
  from r7
  swap
  ibt r8,#127
  and r8
  add r0
  to r14
  add r10
  getb
  inc r14
  getbh
  move r14,r0
  move r1,r5
  getb
  move r11,r0
  ibt r8,#$fe
  and r8
  sms ($001e),r0
  inc r14
  lms r0,($0018)
  cmp r11
  blt scaled_left4
  nop
  move r11,r0
scaled_left4:
  getb
  move r12,r0
  inc r14
  lms r0,($0018)
  add r9
  cmp r12
  bge scaled_right4
  nop
  move r12,r0
scaled_right4:
  from r12
  sub r11
  beq scaled_next4
  nop
  blt scaled_next4
  nop
  move r12,r0
  lms r0,($0018)
  from r11
  sub r0
  with r1
  add r0
  lms r0,($001e)
  from r11
  sub r0
  lsr
  to r14
  add r14
  ibt r8,#1
  from r11
  and r8
  beq scaled_even4
  nop
  getb
  .repeat 4
    lsr
  .endrepeat
  color
  plot
  inc r14
  dec r12
scaled_even4:
  from r12
  and r8
  move r11,r0
  from r12
  lsr
  move r12,r0
  ibt r8,#0
  cmp r8
  beq scaled_tail4
  nop
  iwt r13,#.loword(scaled_pixels4)
scaled_pixels4:
  getb
  inc r14
  color
  plot
  .repeat 4
    lsr
  .endrepeat
  color
  loop
  plot
scaled_tail4:
  from r11
  cmp r8
  beq scaled_next4
  nop
  getc
  plot
scaled_next4:
  with r7
  add r4
  dec r6
  beq scaled_end4
  inc r2
  iwt r8,#.loword(scaled_row4)
  jmp (r8)
  nop
scaled_end4:
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
.align 16,$01
scaled_unpacked4:
  cache
unpacked_row4:
  from r7
  swap
  ibt r8,#127
  and r8
  add r0
  to r14
  add r10
  getb
  inc r14
  getbh
  move r14,r0
  move r1,r5
  getb
  move r11,r0
  sms ($001e),r0
  inc r14
  lms r0,($0018)
  cmp r11
  blt unpacked_left4
  nop
  move r11,r0
unpacked_left4:
  getb
  move r12,r0
  inc r14
  lms r0,($0018)
  add r9
  cmp r12
  bge unpacked_right4
  nop
  move r12,r0
unpacked_right4:
  from r12
  sub r11
  beq unpacked_next4
  nop
  blt unpacked_next4
  nop
  move r12,r0
  lms r0,($0018)
  from r11
  sub r0
  with r1
  add r0
  lms r0,($001e)
  from r11
  sub r0
  to r14
  add r14
  iwt r13,#.loword(unpacked_pixels4)
unpacked_pixels4:
  getc
  inc r14
  loop
  plot
unpacked_next4:
  with r7
  add r4
  dec r6
  beq unpacked_end4
  inc r2
  iwt r8,#.loword(unpacked_row4)
  jmp (r8)
  nop
unpacked_end4:
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
.align 16,$01
integer_render4:
  cache
integer_row4:
  from r3
  swap
  sex
  move r8,r0              ; 整数DUをbyte刻みに。反転時は負のまま加算。
  from r10
  swap
  iwt r11,#$ff
  and r11
  move r14,r0
  from r7
  iwt r11,#$ff00
  and r11
  to r14
  add r14
  move r1,r5
  move r12,r9
  iwt r13,#.loword(integer_pixels4)
integer_pixels4:
  getc
  with r14
  add r8
  loop
  plot
  with r7
  add r4
  dec r6
  beq integer_end4
  inc r2
  iwt r11,#.loword(integer_row4)
  jmp (r11)
  nop
integer_end4:
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
  .include "gsu_dma4.inc"
.repeat 22,I
  .segment .sprintf("ASSET%02X",$44+I)
  .if I = 21
  .incbin .sprintf("assets4/bank%02x.bin",$44+I), 0, $1300
  .else
  .incbin .sprintf("assets4/bank%02x.bin",$44+I)
  .endif
.endrepeat
.segment "SCALE5E"
.incbin "assets4/scale5e.bin"
.segment "SPAN5F"
.incbin "assets4/background4.bin"
