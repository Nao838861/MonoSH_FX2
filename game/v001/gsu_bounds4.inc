
  ; 今回のdirty範囲を32tile列の[minY,maxY]（8行単位、両端を含む）へ記録。
  ; gsu_clear.incが次回clearに、gsu_dma.incが前回との和集合に使う。
  ; $0580+column*2。min=$ffが空の列。透明画素単位の変更検査はしない。
  ; UVのskipXだけ一時保存する。
  iwt r8,#$0016
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
  iwt r8,#$0016
  to r10
  ldw (r8)
  .ifndef FX_STABLE_GSU_CACHE
  iwt r8,#$000a
  ldw (r8)
  .endif
