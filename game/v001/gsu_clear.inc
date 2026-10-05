; 前回描いたtileだけ消す。32列の[min,max]はGSUが管理する。
  iwt r11,#$0700
  ldw (r11)
  ibt r8,#0
  cmp r8
  bne dirty_clear_begin
  nop
  ibt r0,#1
  stw (r11)
  iwt r1,#$2000
  iwt r12,#6144
  iwt r13,#.loword(dirty_first_clear)
  ibt r0,#0
dirty_first_clear:
  stw (r1)
  inc r1
  loop
  inc r1
  iwt r6,#$0580
  ibt r12,#32
  iwt r13,#.loword(dirty_first_bounds)
  iwt r0,#$00ff
dirty_first_bounds:
  stw (r6)
  iwt r10,#$0280
  from r6
  add r10
  move r10,r0
  iwt r0,#$1700
  stw (r10)
  iwt r0,#$00ff
  inc r6
  loop
  inc r6
  bra dirty_clear_done
  nop
dirty_clear_begin:
  iwt r5,#$2000
  iwt r6,#$0580
  ibt r7,#32
  iwt r8,#$00ff
dirty_column:
  iwt r10,#$0280
  from r6
  add r10
  move r10,r0
  ldw (r6)
  stw (r10)
  move r11,r0
  and r8
  move r9,r0
  cmp r8
  beq dirty_column_done
  nop
  from r11
  swap
  and r8
  sub r9
  inc r0
  add r0
  add r0
  add r0
  move r12,r0
  move r0,r9
  add r0
  add r0
  add r0
  add r0
  add r5
  move r1,r0
  iwt r13,#.loword(dirty_column_clear)
  ibt r0,#0
dirty_column_clear:
  stw (r1)
  inc r1
  loop
  inc r1
dirty_column_done:
  iwt r0,#$00ff
  stw (r6)
  inc r6
  inc r6
  iwt r0,#384
  with r5
  add r0
  dec r7
  bne dirty_column
  nop
dirty_clear_done:
