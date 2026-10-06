; 共通packet/clip/UVと同じ512byte cache内。異なる原画・幅でもCBRを保持。
; R3=stride、R4=従来DV、R7=従来V、R10=packed先頭。
; R9=clip後の残り幅（先頭byte途中の1..3画素は事前に幅から引いてある）。
  ibt r8,#3
  from r9
  and r8
  move r11,r0              ; 末尾0..3画素
  from r9
  lsr
  lsr
  move r9,r0               ; 4画素群数
  ibt r8,#$7f
  .ifndef FX_SCALED_CLIP
  iwt r13,#.loword(scaled_pixels)
  .endif
scaled_row:
  from r7
  swap
  and r8
  umult r3                 ; 8bit原画Y*stride。元bankの前半/後半bitは除く。
  to r14
  add r10
  move r1,r5
  move r12,r9
  .ifdef FX_SCALED_CLIP
  lms r0,($001c)
  ibt r13,#0
  cmp r13
  beq scaled_head_done
  nop
  iwt r13,#.loword(scaled_head_draw)
  jmp (r13)
  nop
scaled_head_done:
  iwt r13,#.loword(scaled_pixels)
  .endif
scaled_pixels:
  getb
  inc r14
  .repeat 4,I
    color
    .if I=3
      loop
      plot
    .else
      plot
      lsr
      lsr
    .endif
  .endrepeat
  ibt r0,#0
  from r11
  cmp r0
  beq scaled_next_row
  nop
  move r12,r11
  getb
  .repeat 3,I
    color
    plot
    dec r12
    beq scaled_next_row
    nop
    .if I<2
      lsr
      lsr
    .endif
  .endrepeat
scaled_next_row:
  with r7
  add r4
  dec r6
  bne scaled_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
