; 草・木・敵の透明な左右余白を省く。scaled/generic/準備と同じCBRを使う。
; R0=原画bank内の行表offset。X/Y・DU/DVは従来のQ8.8値。
; 行表のfirst/lastは元の最近傍サンプリングから生成した値なので輪郭を保つ。
; 両端以外の透明画素はPLOTが従来どおり奥の画素を残す。
  move r11,r0
  iwt r13,#.loword(margin_pixel)
margin_row:
  ibt r8,#127
  from r7
  swap
  and r8
  add r0
  to r14
  add r11
  move r1,r5              ; 行表のROM待ちに出力Xの初期化を重ねる。
  getb
  move r10,r0
  inc r14
  ; low8/high8の2積でleft*DUの16bit値を得る。DV/heightを壊さない。
  ; 後半の境界値を読むROM待ちにもこの計算を重ねる。
  from r10
  umult r3
  move r8,r0
  from r3
  swap
  umult r10
  swap
  with r8
  add r0
  getb
  move r12,r0
  from r12
  cmp r9
  blt margin_right_ready
  nop
  move r12,r9
margin_right_ready:
  from r12
  sub r10
  beq margin_next_row
  nop
  blt margin_next_row
  nop
  move r12,r0
  .ifdef FX_GENERIC_PIPELINE
  merge r14
  with r8
  add r3
  with r1
  add r10
  getc
  .else
  with r1
  add r10
  .endif
margin_pixel:
  merge r14
  with r8
  add r3
  .ifdef FX_GENERIC_PIPELINE
  plot
  loop
  getc
  .else
  getc
  loop
  plot
  .endif
margin_next_row:
  with r7
  add r4
  dec r6
  bne margin_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
