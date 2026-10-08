; 次のVRAM面に残る旧画像と、今回の列の範囲の和集合を転送する。
; $0600/$0640=VRAM各面の32列の境界、$1100=16件までのDMA記述子。
plan_dma4:
  cache                   ; 16列の同じloopをROMから毎回fetchしない。
  iwt r8,#$1016
  to r6
  ldw (r8)
  iwt r0,#$0600
  ibt r8,#0
  from r6
  cmp r8
  beq plan_page0
  nop
  iwt r0,#$0640
plan_page0:
  sms ($001c),r0
  iwt r8,#$1010
  ldw (r8)
  ibt r8,#64
  and r8
  lsr
  lsr
  move r7,r0
  iwt r3,#$1100
  ibt r4,#0
  ibt r5,#0
  ibt r12,#16
plan_column4:
  iwt r0,#$0580
  to r1
  add r7
  lms r0,($001c)
  to r2
  add r7
  to r11
  ldw (r2)
  ldw (r1)
  stw (r2)
  move r10,r0
  iwt r8,#255
  and r8
  move r9,r0
  from r10
  swap
  and r8
  move r10,r0
  from r11
  and r8
  cmp r8
  beq plan_old_empty4
  nop
  cmp r9
  bge plan_min_ready4
  nop
  move r9,r0
plan_min_ready4:
  from r11
  swap
  and r8
  cmp r10
  blt plan_old_empty4
  nop
  move r10,r0
plan_old_empty4:
  from r9
  cmp r8
  bne plan_nonempty4
  nop
  iwt r8,#.loword(plan_next4)
  jmp (r8)
  nop
plan_nonempty4:
  from r10
  sub r9
  inc r0
  .repeat 5
    add r0
  .endrepeat
  move r11,r0
  with r5
  add r0
  from r7
  swap
  move r14,r0
  lsr
  add r14
  move r14,r0
  from r9
  add r9
  .repeat 4
    add r0
  .endrepeat
  add r14
  move r14,r0
  ibt r8,#0
  from r4
  cmp r8
  beq plan_new_descriptor4
  nop
  from r14
  cmp r13
  bne plan_new_descriptor4
  nop
  ibt r8,#6
  from r3
  sub r8
  move r8,r0
  ldw (r8)
  add r11
  stw (r8)
  bra plan_source_end4
  nop
plan_new_descriptor4:
  from r11
  stw (r3)
  inc r3
  inc r3
  from r14
  iwt r8,#$2000
  add r8
  stw (r3)
  inc r3
  inc r3
  from r14
  lsr
  add r6
  stw (r3)
  inc r3
  inc r3
  inc r4
plan_source_end4:
  from r14
  to r13
  add r11
plan_next4:
  inc r7
  inc r7
  ibt r8,#15
  from r7
  and r8
  bne plan_column_ready4
  nop
  ibt r8,#16
  with r7
  add r8
plan_column_ready4:
  dec r12
  beq plan_done4
  nop
  iwt r8,#.loword(plan_column4)
  jmp (r8)
  nop
plan_done4:
  iwt r8,#$1160
  from r4
  stw (r8)
  inc r8
  inc r8
  from r5
  stw (r8)
  iwt r8,#.loword(render_stop)
  jmp (r8)
  nop
