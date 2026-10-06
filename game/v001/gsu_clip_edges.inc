; 安定cache構成の座標補正。CACHEを実行せず共通dirty処理へ戻る。
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
  iwt r11,#.loword(clip_done)
  jmp (r11)
  nop
clip_empty:
  ; 全画面外や非正の寸法は、R12=0の画素LOOPへ入れずに次spriteへ進む。
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
