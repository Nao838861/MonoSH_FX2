; CPUの安定ソート済みFxDraw (10byte)をshaderレジスタへ展開する。
; wire: centerX(s16), bottomY(s16), width(u8), height(u8),
;       asset(u8), flags(u8), control(2bytes)。CPU分類時はbit15=完全画面内。
; 旧構成の末尾Z/priorityは読み飛ばす。元FxDrawの並びは変更しない。
; width/heightは投影後の元寸法。R3/R4に残し、clip後もUVの倍率を維持する。
; 出力X=centerX-floor(width/2)、Y=bottomY-height-20（FBの座標原点）。
  .ifdef FX_ROW_MARGINS
  ; 1体につき1回の展開だけcache外へ。行・画素loopの居場所を確保する。
  iwt r10,#.loword(draw_prefix)
  jmp (r10)
  nop
draw_prefix_done:
  .else
  .include "gsu_draw_prefix.inc"
  .endif
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
  .ifdef FX_CPU_CLIP_COMMANDS
  to r13
  ldw (r11)                ; packet末尾の制御word。clip入口までR13に保存。
  .endif
  inc r11
  inc r11
  move r0,r12
  romb
