; CPUの安定ソート済みFxDraw (10byte)をshaderレジスタへ展開する。
; wire: centerX(s16), bottomY(s16), width(u8), height(u8),
;       asset(u8), flags(u8), Z/priority(2bytes)。最後の2bytesは読み飛ばす。
; width/heightは投影後の元寸法。R3/R4に残し、clip後もUVの倍率を維持する。
; 出力X=centerX-floor(width/2)、Y=bottomY-height-20（FBの座標原点）。
  to r1
  ldw (r11)
  inc r11
  inc r11
  to r2
  ldw (r11)
  inc r11
  inc r11
  ldw (r11)
  ; little endianのwidth/heightを分離し、clipで減らす幅R9・高さR6にも複製。
  move r4,r0
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
  move r8,r0                ; low=asset, high=flags
  swap
  ibt r12,#$30
  and r12
  add r0
  add r0
  move r13,r0              ; flip X/Yはmetaのbit6/7
  ibt r12,#63
  from r8
  and r12
  or r13
  move r13,r0              ; assetを含むmeta
  ; ROM bank=$44+(asset/2)。metaのbit0でbank内の前半/後半を選ぶ。
  ; bankを下位byte、asset+flipを上位byteにまとめてUV準備へ渡す。
  from r8
  and r12
  lsr
  ibt r12,#$44
  add r12
  move r8,r0
  from r13
  swap
  or r8
  move r12,r0              ; ROM bank/meta word
  ibt r7,#0
  ibt r8,#1
  from r13
  and r8
  beq draw_base_ready
  nop
  iwt r7,#$8000
draw_base_ready:
  ibt r10,#0
  inc r11
  inc r11
  inc r11
  inc r11                  ; Z/priorityはCPUで並べたので読まない。
  move r0,r12
  romb
