; 横方向だけを同じQ8.8で事前縮小したpacked行を4画素ずつ読む。
; 横clip/X反転/未収録の幅は既存genericへ戻す。縦は従来DVのまま。
; table5F[asset*1024+width*4] = bank(u8), stride(u8), offset(u16)。
.export scaled_select
scaled_select:
  .ifdef FX_SCALED_CLIP
  iwt r8,#$000a
  ldw (r8)
  swap
  ibt r8,#64
  and r8
  bne scaled_fallback
  nop
  .else
  ibt r8,#0
  from r10
  cmp r8
  bne scaled_fallback
  nop
  iwt r8,#$001a
  ldw (r8)
  cmp r9
  bne scaled_fallback
  nop
  .endif
  ibt r8,#8
  from r9
  cmp r8
  blt scaled_fallback
  nop
  bra scaled_lookup
  nop
scaled_restore:
  iwt r8,#$000a
  ldw (r8)
  romb
scaled_fallback:
  iwt r11,#.loword(generic_fallback)
  jmp (r11)
  nop
scaled_lookup:
  iwt r8,#$000a
  ldw (r8)
  swap
  ibt r8,#63
  and r8
  swap
  add r0
  add r0
  move r12,r0
  ibt r0,#$5f
  romb
  .ifdef FX_SCALED_CLIP
  lms r0,($001a)           ; 表はclip前の幅。出力幅R9とは分ける。
  add r0
  .else
  from r9
  add r9
  .endif
  add r0
  to r14
  add r12
  getb
  ibt r8,#0
  cmp r8
  beq scaled_restore
  nop
  inc r14
  getbh
  move r12,r0              ; bank/stride。offsetも同じtable bankから読む。
  inc r14
  getb
  inc r14
  getbh
  move r10,r0              ; 最初の原画行のROM byte位置
  move r0,r12
  romb
  swap
  iwt r8,#$00ff
  and r8
  move r3,r0               ; packed行stride。DUの画素選択は生成時に完了。
  .ifdef FX_SCALED_CLIP
  lms r0,($0018)
  ibt r8,#3
  and r8
  sms ($001c),r0           ; 先頭byteから捨てる0..3画素。4pixel未満の頭だけ別描画。
  beq scaled_head_ready
  nop
  ibt r8,#4
  from r8
  sub r0
  with r9
  sub r0
scaled_head_ready:
  lms r0,($0018)
  lsr
  lsr
  with r10
  add r0
  .endif
  iwt r11,#.loword(scaled_render)
  iwt r8,#.loword(hot_cache)
  jmp (r8)
  nop
