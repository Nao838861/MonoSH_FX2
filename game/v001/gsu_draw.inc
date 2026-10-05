; CPUの安定ソート済みFxDraw (10byte)をshaderレジスタへ展開する。
  to r1
  ldw (r11)
  inc r11
  inc r11
  to r2
  ldw (r11)
  inc r11
  inc r11
  ldw (r11)
  move r4,r0
  iwt r8,#$00ff
  and r8
  move r3,r0
  move r9,r0
  from r4
  swap
  and r8
  move r4,r0
  move r6,r0
  inc r11
  inc r11
  from r3
  lsr
  move r8,r0
  from r1
  sub r8
  move r1,r0
  move r5,r0
  from r2
  sub r4
  ibt r8,#20
  sub r8
  move r2,r0
  ldw (r11)
  move r8,r0                ; low=asset, high=flags
  swap
  ibt r12,#$30
  and r12
  add r0
  add r0
  move r13,r0              ; flip X/Yはmetaのbit6/7
  ibt r12,#63
  from r8
  and r12
  or r13
  move r13,r0              ; assetを含むmeta
  from r8
  and r12
  lsr
  ibt r12,#$44
  add r12
  move r8,r0
  from r13
  swap
  or r8
  move r12,r0              ; ROM bank/meta word
  ibt r7,#0
  ibt r8,#1
  from r13
  and r8
  beq draw_base_ready
  nop
  iwt r7,#$8000
draw_base_ready:
  ibt r10,#0
  inc r11
  inc r11
  inc r11
  inc r11                  ; Z/priorityはCPUで並べたので読まない。
  move r0,r12
  romb
