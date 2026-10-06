; 原画のskipなし・反転なしではDU/DV表を読むだけでよい。
; clip後height/base Vをレジスタのまま保ち、zero*DU/DVのLMULTとRAM退避を省く。
  sms ($001a),r3
  lms r0,($000a)
  move r11,r0
  iwt r8,#$c000
  and r8
  or r10
  move r13,r0
  iwt r8,#$00ff
  from r7
  and r8
  or r13
  beq uv_fast_tables
  nop
  iwt r8,#.loword(uv_slow)
  jmp (r8)
  nop
uv_fast_tables:
  from r11
  swap
  ibt r8,#63
  and r8
  swap
  add r0
  move r12,r0
  ibt r0,#$5e
  romb
  from r3
  add r3
  to r14
  add r12
  getb
  inc r14
  getbh
  move r3,r0
  from r4
  add r4
  add r12
  iwt r8,#$5800
  to r14
  add r8
  getb
  inc r14
  getbh
  move r4,r0
  move r0,r11
  romb
uv_fast_done:
