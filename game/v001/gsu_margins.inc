; 非ボスの任意倍率を、透明な左右余白だけ省いて描く。
; 草0/1・木4・敵36の[最初の出力X, 最後の出力X+1]を原画bankの空白へ置く。
; bank5Eの$B058+slot*512+rawWidth*2から行表のoffsetを読む。
; 画像データは最大原画だけ。X反転・左clip・未対応幅は従来へ戻る。
; 右clip・上下clip・Y反転は行表と同じQ8.8位置で処理する。
.export margin_select
margin_select:
  ibt r8,#0
  from r10
  cmp r8
  bne margin_reject
  nop
  lms r0,($000a)
  swap
  ibt r8,#127
  and r8
  move r12,r0
  ibt r8,#2
  cmp r8
  blt margin_grass
  nop
  ibt r8,#4
  cmp r8
  beq margin_tree
  nop
  ibt r8,#36
  cmp r8
  bne margin_reject
  nop
  iwt r12,#$b658
  bra margin_lookup
  nop
margin_tree:
  iwt r12,#$b458
  bra margin_lookup
  nop
margin_grass:
  from r12
  swap
  add r0
  iwt r8,#$b058
  add r8
  move r12,r0
margin_lookup:
  ibt r8,#32
  from r6
  cmp r8
  blt margin_reject        ; 小さい絵は行表の参照・入口の準備費用が勝つ。
  nop
  ibt r0,#$5e
  romb
  lms r0,($001a)
  add r0
  to r14
  add r12
  getb
  inc r14
  getbh
  move r11,r0
  lms r0,($000a)
  romb
  ibt r8,#0
  from r11
  cmp r8
  beq margin_reject
  nop
  move r0,r11             ; 共通cache入口が使うR11と表offsetを分ける。
  iwt r11,#.loword(margin_render)
  iwt r8,#.loword(hot_cache)
  jmp (r8)
  nop
margin_reject:
  iwt r11,#.loword(margin_generic)
  jmp (r11)
  nop
