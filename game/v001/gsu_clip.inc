; CPUがソートした生の矩形をGSUでclipする。部分転送の既定構成でも使用。
; 出力をX=[0,256)、Y=[0,192)へ制限。各辺の判定はspriteごとに1回だけ。
; 左/上を切った量は原画UVの開始位置へ反映し、倍率はclip前の寸法を使う。
; 原画のskipXはR10、skipYはR13→R7下位byteへ。幅R9・高さR6を減らす。
; R0=bank/metaをscratchへ保存。描画しない場合もpacketは既に進めてある。
  iwt r8,#$000a
  stw (r8)
  .ifdef FX_CPU_CLIP_COMMANDS
  ibt r8,#0
  from r13
  cmp r8
  bmi clip_done            ; INSIDEなら座標補正・skip計算を省略。
  nop
  .endif
  .ifdef FX_STABLE_GSU_CACHE
  iwt r11,#.loword(clip_edges)
  jmp (r11)                ; cache外のclipへ。同じCBRを維持する。
  nop
  .else
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
  bra clip_done
  nop
clip_empty:
  ; 全画面外や非正の寸法は、R12=0の画素LOOPへ入れずに次spriteへ進む。
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
  .endif
clip_done:
  ; 今回のdirty範囲を32tile列の[minY,maxY]（8行単位、両端を含む）へ記録。
  ; gsu_clear.incが次回clearに、gsu_dma.incが前回との和集合に使う。
  ; $0580+column*2。min=$ffが空の列。透明画素単位の変更検査はしない。
  ; UVのskipXだけ一時保存する。
  iwt r8,#$0018
  from r10
  stw (r8)
  from r2
  lsr
  lsr
  lsr
  move r14,r0
  from r2
  add r6
  dec r0
  lsr
  lsr
  lsr
  move r8,r0
  from r1
  add r9
  dec r0
  lsr
  lsr
  lsr
  add r0
  iwt r13,#$0580
  with r13
  add r0
  from r1
  lsr
  lsr
  lsr
  add r0
  iwt r11,#$0580
  with r11
  add r0
clip_bounds_column:
  ldb (r11)
  cmp r14
  blt clip_bounds_min_ready
  nop
  from r14
  stb (r11)
clip_bounds_min_ready:
  inc r11
  ldb (r11)
  cmp r8
  bge clip_bounds_max_ready
  nop
  from r8
  stb (r11)
clip_bounds_max_ready:
  inc r11
  from r11
  cmp r13
  blt clip_bounds_column
  nop
  beq clip_bounds_column
  nop
  iwt r8,#$0018
  to r10
  ldw (r8)
  .ifndef FX_STABLE_GSU_CACHE
  iwt r8,#$000a
  ldw (r8)
  .endif
