; 元の任意倍率kernel。横clip・X反転・ROM表にない幅を受け持つ。
  iwt r13,#.loword(pixel)
row:
  move r1,r5
  move r8,r10
  move r12,r9
pixel:
  merge r14
  with r8
  add r3
  getc
  loop
  plot
  with r7
  add r4
  dec r6
  bne row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
