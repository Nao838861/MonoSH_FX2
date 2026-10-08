; 前回描いたtileだけ消す。32列の[min,max]はGSUが管理する。
; $0700=初期化済みflag、$0580=直前の範囲（描画後は今回の範囲）、
; $0800=前回の範囲を退避する領域。空はmin=$ff。
; FBは列優先: 1tile=32bytes、1列=24tiles=768bytes。
; 全画素PLOTで消すより、連続したtile領域へSTWで0を書く方を選んでいる。
  iwt r11,#$0700
  ldw (r11)
  ibt r8,#0
  cmp r8
  bne dirty_clear_begin
  nop
  ibt r0,#1
  stw (r11)
  iwt r1,#$2000
  iwt r12,#3072
  iwt r13,#.loword(dirty_first_clear)
  ibt r0,#0
dirty_first_clear:
  ; 初回だけ24,576bytes全体を0へ。3,072回のloopで各8bytes進める。
  .repeat 3
  stw (r1)
  inc r1
  inc r1
  .endrepeat
  stw (r1)
  inc r1
  loop
  inc r1
  iwt r6,#$0580
  ibt r12,#32
  iwt r13,#.loword(dirty_first_bounds)
  iwt r0,#$00ff
dirty_first_bounds:
  ; 今回の列を空にし、前回側は[0,23]にする。初回DMAも全FBを反映させる。
  stw (r6)
  iwt r10,#$0080
  from r6
  add r10
  move r10,r0
  iwt r0,#$00ff
  stw (r10)
  ibt r8,#64
  with r10
  add r8
  stw (r10)
  iwt r10,#$0280
  from r6
  add r10
  move r10,r0
  iwt r0,#$1700
  stw (r10)
  iwt r0,#$00ff
  inc r6
  loop
  inc r6
  bra dirty_clear_done
  nop
dirty_clear_begin:
  iwt r11,#$1010
  ldw (r11)
  lsr
  lsr
  iwt r8,#$0580
  add r8
  move r6,r0
  ldw (r11)
  .repeat 5
    add r0
  .endrepeat
  move r5,r0
  add r0
  add r5
  iwt r8,#$2000
  add r8
  move r5,r0
  ibt r7,#8
  iwt r8,#$00ff
dirty_column:
  iwt r10,#$0280
  from r6
  add r10
  move r10,r0
  ldw (r6)
  stw (r10)                ; 直前の範囲を$0800へ保存。消去跡のDMAにも必要。
  move r11,r0
  and r8
  move r9,r0
  cmp r8
  beq dirty_column_done
  nop
  from r11
  swap
  and r8
  sub r9
  inc r0
  ; 1tileの32bytesを4wordずつ消す。tile数×4回のloop。
  add r0
  add r0
  add r0
  add r0
  lsr
  lsr
  move r12,r0
  move r0,r9
  add r0
  add r0
  add r0
  add r0
  add r0
  add r5
  move r1,r0
  iwt r13,#.loword(dirty_column_clear)
  ibt r0,#0
dirty_column_clear:
  .repeat 3
  stw (r1)
  inc r1
  inc r1
  .endrepeat
  stw (r1)
  inc r1
  loop
  inc r1
dirty_column_done:
  ; 今回の範囲を空へ戻す。描画中のgsu_clip.incが改めてmin/maxを更新する。
  iwt r0,#$00ff
  stw (r6)
  inc r6
  inc r6
  iwt r0,#768
  with r5
  add r0
  dec r7
  bne dirty_column
  nop
dirty_clear_done:
