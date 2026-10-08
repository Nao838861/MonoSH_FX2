.include "casfx.inc"
; 4bpp実験専用。ゲームのpacket/clip/UV規則は60fps版と共用する。
.segment "GSU"
.export render_entry, render_stop, background_done, dispatch_nonzero, generic, margin_render, scaled_render4
.align 16
render_entry:
  cache
  sub r0
  cmode
  .include "gsu_clear4.inc"
  iwt r11,#$1000
  ibt r10,#2
background_layer:
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
  cache
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
  iwt r11,#$8000
  ldw (r11)
  iwt r8,#4
  stw (r8)
  inc r11
  inc r11
  iwt r8,#6
  from r11
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
  to r1
  ldw (r11)
  inc r11
  inc r11
  to r2
  ldw (r11)
  inc r11
  inc r11
  to r3
  ldw (r11)
  inc r11
  inc r11
  to r4
  ldw (r11)
  inc r11
  inc r11
  to r5
  ldw (r11)
  inc r11
  inc r11
  to r6
  ldw (r11)
  inc r11
  inc r11
  to r7
  ldw (r11)
  inc r11
  inc r11
  to r9
  ldw (r11)
  inc r11
  inc r11
  to r10
  ldw (r11)
  inc r11
  inc r11
  ldw (r11)
  romb
  sms ($000a),r0
  inc r11
  inc r11
  ldw (r11)
  sms ($001a),r0
  inc r11
  inc r11
  ldw (r11)
  sms ($0018),r0
  inc r11
  inc r11
  iwt r8,#6
  from r11
  stw (r8)
  iwt r8,#$1010
  to r11
  ldw (r8)
  from r1
  add r9
  cmp r11
  blt :+
  nop
  bne strip_right_visible
  nop
:
  iwt r8,#.loword(dispatch)
  jmp (r8)
  nop
strip_right_visible:
  ibt r8,#64
  with r11
  add r8
  from r1
  cmp r11
  blt strip_left_visible
  nop
  iwt r8,#.loword(dispatch)
  jmp (r8)
  nop
strip_left_visible:
  from r1
  add r9
  cmp r11
  blt strip_end_ready
  nop
  move r0,r11
strip_end_ready:
  to r9
  sub r1
  ibt r8,#64
  with r11
  sub r8
  from r11
  sub r1
  ibt r8,#0
  cmp r8
  blt strip_skip_ready
  nop
  beq strip_skip_ready
  nop
  move r11,r0
  with r9
  sub r11
  with r1
  add r11
  sms ($0020),r4
  sms ($0022),r6
  move r6,r3
  from r11
  lmult
  with r10
  add r4
  lms r4,($0020)
  lms r6,($0022)
  lms r0,($0018)
  add r11
  sms ($0018),r0
strip_skip_ready:
  move r5,r1
  .include "gsu_bounds4.inc"
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
  iwt r11,#.loword(generic)
  jmp (r11)
  nop
.align 16,$01
generic:
  cache
  .include "gsu_generic_pipeline.inc"
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
  bne render_stop
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
render_stop:
  stop
  nop

; ボス3原画を同じQ8.8で水平縮小済み。縦の倍率・clip・Y反転は実行時のまま。
scaled_select4:
  lms r0,($000a)
  swap
  ibt r8,#64
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
  bne scaled_reject4
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
  romb
  swap
  iwt r8,#255
  and r8
  move r3,r0
  iwt r11,#.loword(scaled_render4)
  jmp (r11)
  nop
scaled_reject4:
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
.repeat 22,I
  .segment .sprintf("ASSET%02X",$44+I)
  .incbin .sprintf("assets4/bank%02x.bin",$44+I)
.endrepeat
.segment "SCALE5E"
.incbin "assets4/scale5e.bin"
.segment "SPAN5F"
.incbin "assets4/background4.bin"
