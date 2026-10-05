; CPUがソートした生の矩形をGSUでclipする。全FB転送時だけ使用。
  iwt r8,#$000a
  stw (r8)
  ibt r8,#0
  from r1
  cmp r8
  bpl clip_x_positive
  nop
  ibt r0,#0
  sub r1
  move r10,r0
  with r9
  add r1
  ibt r1,#0
clip_x_positive:
  from r1
  add r9
  iwt r8,#256
  cmp r8
  blt clip_x_ready
  nop
  iwt r0,#256
  to r9
  sub r1
clip_x_ready:
  ibt r8,#0
  from r9
  cmp r8
  beq clip_empty
  nop
  bmi clip_empty
  nop
  ibt r13,#0
  from r2
  cmp r8
  bpl clip_y_positive
  nop
  ibt r0,#0
  sub r2
  move r13,r0
  with r6
  add r2
  ibt r2,#0
clip_y_positive:
  from r2
  add r6
  iwt r8,#192
  cmp r8
  blt clip_y_ready
  nop
  iwt r0,#192
  to r6
  sub r2
clip_y_ready:
  ibt r8,#0
  from r6
  cmp r8
  beq clip_empty
  nop
  bmi clip_empty
  nop
  move r5,r1
  with r7
  or r13
  bra clip_done
  nop
clip_empty:
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
clip_done:
  ; 次回clear用の範囲。UVのskipXだけ一時保存する。
  iwt r8,#$0018
  from r10
  stw (r8)
  from r2
  lsr
  lsr
  lsr
  move r14,r0
  from r2
  add r6
  dec r0
  lsr
  lsr
  lsr
  move r8,r0
  from r1
  add r9
  dec r0
  lsr
  lsr
  lsr
  add r0
  iwt r13,#$0580
  with r13
  add r0
  from r1
  lsr
  lsr
  lsr
  add r0
  iwt r11,#$0580
  with r11
  add r0
clip_bounds_column:
  ldb (r11)
  cmp r14
  blt clip_bounds_min_ready
  nop
  from r14
  stb (r11)
clip_bounds_min_ready:
  inc r11
  ldb (r11)
  cmp r8
  bge clip_bounds_max_ready
  nop
  from r8
  stb (r11)
clip_bounds_max_ready:
  inc r11
  from r11
  cmp r13
  blt clip_bounds_column
  nop
  beq clip_bounds_column
  nop
  iwt r8,#$0018
  to r10
  ldw (r8)
  iwt r8,#$000a
  ldw (r8)
