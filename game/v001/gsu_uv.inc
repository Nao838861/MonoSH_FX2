; wireの生寸法・整数skipを、既存shaderのQ8.8レジスタへ変換する。
; scratch: $A bank/meta, $10 height, $12 base V, $14 skip Y。
  cache
  iwt r8,#$000a
  stw (r8)                 ; r0はbank/meta。ROMBは下7bitだけを読む。
  iwt r8,#$0010
  from r6
  stw (r8)
  iwt r8,#$0012
  iwt r13,#$ff00
  from r7
  and r13
  stw (r8)
  iwt r8,#$0014
  iwt r13,#$00ff
  from r7
  and r13
  stw (r8)
  iwt r8,#$000a
  ldw (r8)
  swap
  iwt r8,#$00ff
  and r8
  move r11,r0              ; meta
  ibt r8,#63
  and r8
  .repeat 9
    add r0
  .endrepeat
  move r12,r0              ; asset*512
  ibt r0,#$5e
  romb
  from r3
  add r3
  to r14
  add r12
  getb
  inc r14
  getbh
  move r3,r0               ; DU
  from r4
  add r4
  add r12
  iwt r8,#$5800
  to r14
  add r8
  getb
  inc r14
  getbh
  move r4,r0               ; DV
  move r13,r4
  move r6,r3
  from r10
  lmult                    ; U0=skip X*DU、low16はR4
  move r10,r4
  move r4,r13
  ibt r8,#64
  from r11
  and r8
  beq uv_u_done
  nop
  ibt r0,#0
  to r3
  sub r3
  ibt r8,#63
  from r11
  and r8
  iwt r8,#$b000
  to r14
  add r8
  getb
  swap
  dec r0
  to r10
  sub r10
uv_u_done:
  move r13,r4
  move r6,r4
  iwt r8,#$0014
  ldw (r8)
  lmult                    ; V skipもlow16だけを使う。
  move r7,r4
  move r4,r13
  ibt r8,#$80
  from r11
  and r8
  beq uv_v_done
  nop
  ibt r0,#0
  to r4
  sub r4
  ibt r8,#63
  from r11
  and r8
  iwt r8,#$b02c
  to r14
  add r8
  getb
  swap
  dec r0
  to r7
  sub r7
uv_v_done:
  iwt r8,#$0012
  ldw (r8)
  move r8,r0
  with r7
  or r8
  iwt r8,#$0010
  to r6
  ldw (r8)
  iwt r8,#$000a
  ldw (r8)
  romb
