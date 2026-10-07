; 現画素のCOLORを保持したまま、次のROM読出しを開始する。
; WITH/ADD/PLOT/LOOPをROM待ちへ重ね、GETCをLOOPのdelay slotへ置く。
; 各行の最後にも1画素分を先読みするが、その色は描かない。
; Uは符号付きQ8.8のままなので、幅1・clip・X/Y反転にも同じ画素を描く。
  iwt r13,#.loword(pipeline_pixel)
pipeline_row:
  move r1,r5
  move r8,r10
  move r12,r9
  merge r14
  with r8
  add r3
  getc
pipeline_pixel:
  merge r14
  with r8
  add r3
  plot
  loop
  getc
  with r7
  add r4
  dec r6
  bne pipeline_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
