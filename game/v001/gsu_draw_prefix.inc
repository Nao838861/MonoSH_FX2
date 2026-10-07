; 座標・寸法・asset/flipの展開。R11=packet、R10は戻り先に使える。
; 出口: R13=asset+flip、R8=元asset/flags、R12=63。
; この部分だけをROMから実行し、CBRを変更せず511byteの共通部分へ戻る。
; 元のcenter/bottom座標から左上を求めるため、ゲーム側の座標系は変えない。
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
  ; little endianのwidth/heightを分離し、clip後用のR9/R6にも複製。
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
  move r8,r0
  ; flagsのbit4/5を、ROM bankと組み合わせるmetaのbit6/7へ移す。
  swap
  ibt r12,#$30
  and r12
  add r0
  add r0
  move r13,r0
  ibt r12,#63
  from r8
  and r12
  or r13
  move r13,r0
