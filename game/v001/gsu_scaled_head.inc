; 横clipでpacked byteの途中から始まる最大3画素だけを処理する。
; CACHEを変更せず共通cacheへ戻る。入口R0=捨てる1..3画素、R12=主loop群数。
scaled_head_draw:
  ibt r13,#4
  with r13
  sub r0                   ; 描く頭は4-skip画素。clip後幅>=8なので常に全部描く。
  dec r0
  beq scaled_skip_one
  nop
  dec r0
  beq scaled_skip_two
  nop
  getb
  .repeat 6
    lsr
  .endrepeat
  bra scaled_head_pixel
  nop
scaled_skip_two:
  getb
  .repeat 4
    lsr
  .endrepeat
  bra scaled_head_pixel
  nop
scaled_skip_one:
  getb
  lsr
  lsr
scaled_head_pixel:
  color
  plot
  dec r13
  beq scaled_head_exit
  nop
  lsr
  lsr
  bra scaled_head_pixel
  nop
scaled_head_exit:
  inc r14
  iwt r13,#.loword(scaled_head_done)
  jmp (r13)
  nop
