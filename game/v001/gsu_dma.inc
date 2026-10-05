; 前回・今回の和集合からVRAM DMAの区間を生成する。
; 64byte以内の隙間もまとめる。header8=count、headerA=bytes。
  ibt r5,#0
  iwt r6,#$0800
  ibt r7,#32
  iwt r8,#$00ff
  iwt r11,#$0600
  ibt r12,#0
  ibt r13,#0
  ibt r14,#0
gsu_dma_column:
  ldw (r6)
  move r4,r0
  iwt r10,#$0280
  with r6
  sub r10
  ldw (r6)
  move r3,r0
  with r6
  add r10
  ; 各spriteで和集合を重ねず、描画後に32列だけ比較する。
  from r4
  and r8
  move r1,r0
  from r3
  and r8
  cmp r1
  bge gsu_union_min
  nop
  move r1,r0
gsu_union_min:
  from r4
  swap
  and r8
  move r2,r0
  from r3
  swap
  and r8
  cmp r2
  bge gsu_union_max
  nop
  move r0,r2
gsu_union_max:
  swap
  move r4,r0
  from r1
  or r4
  move r4,r0
  and r8
  move r1,r0
  cmp r8
  beq gsu_dma_next
  nop
  add r0
  add r0
  add r0
  add r5
  move r9,r0
  from r4
  swap
  and r8
  sub r1
  inc r0
  add r0
  add r0
  add r0
  add r0
  move r10,r0
  ibt r0,#0
  from r12
  cmp r0
  beq gsu_dma_new
  nop
  from r9
  sub r14
  ibt r3,#33
  cmp r3
  bge gsu_dma_new
  nop
  add r0
  add r10
  move r3,r0
  dec r11
  dec r11
  ldw (r11)
  add r3
  stw (r11)
  inc r11
  inc r11
  bra gsu_dma_end
  nop
gsu_dma_new:
  from r9
  stw (r11)
  inc r11
  inc r11
  from r10
  stw (r11)
  inc r11
  inc r11
  inc r12
  move r3,r10
gsu_dma_end:
  with r13
  add r3
  from r10
  lsr
  add r9
  move r14,r0
gsu_dma_next:
  inc r6
  inc r6
  iwt r0,#192
  with r5
  add r0
  dec r7
  beq gsu_dma_columns_done
  nop
  iwt r10,#.loword(gsu_dma_column)
  jmp (r10)
  nop
gsu_dma_columns_done:
  move r0,r12
  .repeat 6
    add r0
  .endrepeat
  add r13
  iwt r8,#12000
  cmp r8
  blt gsu_dma_store
  nop
  iwt r11,#$0600
  ibt r0,#0
  stw (r11)
  inc r11
  inc r11
  iwt r0,#12288
  stw (r11)
  ibt r12,#1
  iwt r13,#12288
gsu_dma_store:
  iwt r11,#$0008
  from r12
  stw (r11)
  inc r11
  inc r11
  from r13
  stw (r11)
