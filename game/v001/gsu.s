.include "casfx.inc"
.segment "GSU"
.export render_entry, render_stop
.export packed_one, packed_half, packed_quarter, packed_double
.export packed_mirror_one, packed_mirror_half, packed_mirror_quarter
.align 16
render_entry:
  cache
  sub r0
  cmode
  .ifdef FX_GSU_CLIP
  .include "gsu_clear.inc"
  .else
  ; 初回は全FB、その後は前回・今回のtile範囲だけを0へ戻す。
  iwt r11,#$0008
  ldw (r11)
  move r9,r0
  iwt r10,#$0600
clear_span:
  ibt r0,#0
  from r9
  cmp r0
  beq clear_done
  nop
  dec r9
  to r0
  ldw (r10)
  add r0
  iwt r8,#$2000
  to r1
  add r8
  inc r10
  inc r10
  ldw (r10)
  lsr
  move r12,r0
  inc r10
  inc r10
  iwt r13,#.loword(clear_loop)
  sub r0
clear_loop:
  stw (r1)
  inc r1
  loop
  inc r1
  bra clear_span
  nop
clear_done:
  .endif
  iwt r11,#$0000
  ldw (r11)
  iwt r11,#$0004
  stw (r11)
  iwt r0,#$0020
  iwt r11,#$0006
  stw (r11)
dispatch:
  iwt r11,#$0004
  ldw (r11)
  ibt r8,#0
  cmp r8
  bne dispatch_nonzero
  nop
  iwt r11,#.loword(finished)
  jmp (r11)
  nop
dispatch_nonzero:
  dec r0
  stw (r11)
  iwt r11,#$0006
  ldw (r11)
  move r11,r0
  .ifdef FX_GSU_CLIP
    .include "gsu_draw.inc"
  .else
  to r1
  ldw (r11)
  inc r11
  inc r11
  to r2
  ldw (r11)
  inc r11
  inc r11
  to r3
  ldw (r11)
  inc r11
  inc r11
  to r4
  ldw (r11)
  inc r11
  inc r11
  to r5
  ldw (r11)
  inc r11
  inc r11
  to r6
  ldw (r11)
  inc r11
  inc r11
  to r7
  ldw (r11)
  inc r11
  inc r11
  to r9
  ldw (r11)
  inc r11
  inc r11
  to r10
  ldw (r11)
  inc r11
  inc r11
  ldw (r11)
  romb
  inc r11
  inc r11
  .endif
  iwt r8,#$0006
  from r11
  stw (r8)
  .ifdef FX_GSU_CLIP
    .include "gsu_clip.inc"
  .endif
  .ifdef FX_GSU_UV
    .include "gsu_uv.inc"
  .endif
  cache
  ; 整数の水平stepと4texel境界のclipなら、同じ画素をpackedで読む。
  iwt r8,#$03ff
  from r10
  and r8
  beq positive_steps
  nop
  cmp r8
  bne generic
  nop
  iwt r0,#$ff00
  from r3
  cmp r0
  beq mirror_one_check
  nop
  iwt r0,#$fe00
  from r3
  cmp r0
  beq mirror_half_check
  nop
  iwt r0,#$fc00
  from r3
  cmp r0
  beq mirror_quarter_jump
  nop
  bra generic
  nop
positive_steps:
  iwt r0,#$0080
  from r3
  cmp r0
  beq packed_double_check
  nop
  iwt r0,#$0100
  from r3
  cmp r0
  beq packed_one_check
  nop
  iwt r0,#$0200
  from r3
  cmp r0
  beq packed_half_check
  nop
  iwt r0,#$0400
  from r3
  cmp r0
  beq packed_quarter_jump
  nop
generic:
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
mirror_one_check:
  ibt r8,#3
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_mirror_one)
  jmp (r11)
  nop
mirror_half_check:
  ibt r8,#1
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_mirror_half)
  jmp (r11)
  nop
mirror_quarter_jump:
  iwt r11,#.loword(packed_mirror_quarter)
  jmp (r11)
  nop
packed_double_check:
  ibt r0,#8
  from r9
  cmp r0
  blt generic
  nop
  iwt r11,#.loword(packed_double)
  jmp (r11)
  nop
packed_one_check:
  ibt r8,#3
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_one)
  jmp (r11)
  nop
packed_half_check:
  ibt r8,#1
  from r9
  and r8
  bne generic
  nop
  iwt r11,#.loword(packed_half)
  jmp (r11)
  nop
packed_quarter_jump:
  iwt r11,#.loword(packed_quarter)
  jmp (r11)
  nop
.macro PACKED_GAME name, shift, mirror
  .local packed_row, packed_pixels
name:
  from r10
  .repeat 10
    lsr
  .endrepeat
  iwt r8,#(128+32*mirror)
  to r10
  add r8
  iwt r8,#$ff00
  .if shift < 2
    from r9
    .repeat 2-shift
      lsr
    .endrepeat
    move r9,r0
  .endif
  cache
  iwt r13,#.loword(packed_pixels)
packed_row:
  from r7
  and r8
  to r14
  or r10
  move r1,r5
  move r12,r9
packed_pixels:
  getb
  .if mirror
    dec r14
  .else
    inc r14
  .endif
  .repeat (4>>shift), I
    color
    .if I = (4>>shift)-1
      loop
      plot
    .else
      plot
      .repeat (2<<shift)
        lsr
      .endrepeat
    .endif
  .endrepeat
  with r7
  add r4
  dec r6
  bne packed_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
.endmacro
PACKED_GAME packed_one,0,0
PACKED_GAME packed_half,1,0
PACKED_GAME packed_quarter,2,0
PACKED_GAME packed_mirror_one,0,1
PACKED_GAME packed_mirror_half,1,1
PACKED_GAME packed_mirror_quarter,2,1
; 水平2倍は4原画画素を一度に取得する。8px未満の末尾も同じ色で描く。
packed_double:
  ibt r8,#7
  from r9
  and r8
  move r11,r0
  from r9
  lsr
  lsr
  lsr
  move r9,r0
  from r10
  .repeat 10
    lsr
  .endrepeat
  iwt r8,#128
  to r10
  add r8
  iwt r8,#$ff00
  cache
  iwt r13,#.loword(double_pixels)
double_row:
  from r7
  and r8
  to r14
  or r10
  move r1,r5
  move r12,r9
double_pixels:
  getb
  inc r14
  .repeat 4,I
    color
    plot
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
  beq double_next_row
  nop
  move r12,r11
  getb
  .repeat 7,I
    .if (I & 1)=0
      color
    .endif
    plot
    dec r12
    beq double_next_row
    nop
    .if (I & 1)=1
      lsr
      lsr
    .endif
  .endrepeat
double_next_row:
  with r7
  add r4
  dec r6
  bne double_row
  inc r2
  rpix
  iwt r11,#.loword(dispatch)
  jmp (r11)
  nop
finished:
  rpix
  .if .defined(FX_GSU_CLIP) .and .not .defined(FX_FULL_TRANSFER)
  .include "gsu_dma.inc"
  .endif
  iwt r11,#$0000
  ldw (r11)
render_stop:
  stop
  nop
.repeat 22,I
  .segment .sprintf("ASSET%02X",$44+I)
  .incbin .sprintf("assets/bank%02x.bin",$44+I)
.endrepeat
.segment "SCALE5E"
.incbin "assets/scale5e.bin"
