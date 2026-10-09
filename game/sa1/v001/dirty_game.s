; 直前のpacketとの差分矩形を8x8タイルに丸める。
; framebufferは直前画像を維持し、VRAMの交互二面には2フレーム分の変更を送る。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_plan_dirty: far, sa1_prepare_transfer: far
.import sa1_find_shape: far
.segment "BOOT"
dirty_count=$a0
dirty_i=$a2
dirty_ptr=$a4
dirty_left=$a8
dirty_right=$aa
dirty_top=$ac
dirty_bottom=$ae
dirty_width=$b0
dirty_height=$b2
dirty_max=$b4
transferptr=$b8
sa1_plan_dirty:
  rep #$30
  ldx #0
dirty_init:
  lda #128
  sta $0120,x
  stz $0122,x
  inx
  inx
  inx
  inx
  cpx #96
  bne dirty_init
  lda $0106
  sta dirty_count
  cmp $010e
  bcs :+
  lda $010e
:
  sta dirty_max
  stz dirty_i
  ldx #0
dirty_compare:
  lda dirty_i
  cmp dirty_max
  jcs dirty_bg
  cmp dirty_count
  bcs dirty_changed
  cmp $010e
  bcs dirty_changed
  lda f:$430000,x
  cmp f:$431000,x
  bne dirty_changed
  lda f:$430002,x
  cmp f:$431002,x
  bne dirty_changed
  lda f:$430004,x
  cmp f:$431004,x
  bne dirty_changed
  lda f:$430006,x
  cmp f:$431006,x
  bne dirty_changed
  ; 並べ替え済みの同じ位置なので、Z/priorityだけの変更は画素を変えない。
  ; 順序が変われば先頭8byteの相違として旧・新両方を再描画する。
  bra dirty_next
dirty_changed:
  phx
  lda dirty_i
  cmp dirty_count
  bcs :+
  lda #0
  sta dirty_ptr
  jsr dirty_mark
:
  plx
  phx
  lda dirty_i
  cmp $010e
  bcs :+
  lda #$1000
  sta dirty_ptr
  jsr dirty_mark
:
  plx
dirty_next:
  txa
  clc
  adc #10
  tax
  inc dirty_i
  jmp dirty_compare
dirty_bg:
  lda $0108
  cmp $0110
  bne dirty_background
  lda $010a
  cmp $0112
  bne dirty_background
  lda $010c
  cmp $0114
  beq dirty_save
dirty_background:
  ; 動く二層の背景は旧位置・新位置を含む矩形を無条件に再合成する。
  lda $010c
  cmp $0114
  bcc :+
  lda $0114
:
  clc
  adc #77
  sta dirty_top
  lda $010c
  cmp $0114
  bcs :+
  lda $0114
:
  clc
  adc #91
  sta dirty_bottom
  stz dirty_left
  lda #128
  sta dirty_right
  jsr dirty_rect
dirty_save:
  lda $0108
  sta $0110
  lda $010a
  sta $0112
  lda $010c
  sta $0114
  lda $0106
  sta $010e
  ldx #0
dirty_copy:
  cpx dirty_max
  bcs dirty_first
  ; dirty_maxをbyte数へ変更する代わりに、packet数を別に数える。
  bra dirty_copy_prepare
dirty_copy_prepare:
  lda dirty_count
  asl
  asl
  clc
  adc dirty_count
  asl
  tay
  beq dirty_first
dirty_copy_words:
  lda f:$430000,x
  sta f:$431000,x
  inx
  inx
  dey
  dey
  bne dirty_copy_words
dirty_first:
  lda $0116
  cmp #3
  bcs dirty_return
  inc $0116
  cmp #2
  bcs dirty_return
  ldx #0
dirty_full:
  stz $0120,x
  lda #128
  sta $0122,x
  inx
  inx
  inx
  inx
  cpx #96
  bne dirty_full
dirty_return:
  rtl
dirty_mark:
  txa
  clc
  adc dirty_ptr
  tax
  lda f:$430004,x
  and #255
  sta dirty_width
  lsr
  sta dirty_left
  lda f:$430000,x
  sec
  sbc dirty_left
  sta dirty_left
  clc
  adc dirty_width
  sta dirty_right
  lda f:$430005,x
  and #255
  sta dirty_height
  lda f:$430002,x
  sec
  sbc #20
  sta dirty_bottom
  sec
  sbc dirty_height
  sta dirty_top
  .ifdef SA1_PADDED
  lda f:$430004,x
  sta dirty_width
  lda f:$430006,x
  and #255
  tax
  lda dirty_width
  jsl sa1_find_shape
  lda f:$ff0003,x
  and #255
  clc
  adc dirty_left
  sta dirty_width
  lda f:$ff0005,x
  and #255
  clc
  adc dirty_left
  sta dirty_right
  lda dirty_width
  sta dirty_left
  lda f:$ff0004,x
  and #255
  clc
  adc dirty_top
  sta dirty_height
  lda f:$ff0006,x
  and #255
  clc
  adc dirty_top
  sta dirty_bottom
  lda dirty_height
  sta dirty_top
  .endif
  lda dirty_left
  bpl :+
  lda #0
:
  cmp #256
  jcs dirty_mark_done
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  sta dirty_left
  lda dirty_right
  jmi dirty_mark_done
  cmp #257
  bcc :+
  lda #256
:
  clc
  adc #7
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  sta dirty_right
dirty_rect:
  lda dirty_top
  bpl :+
  lda #0
:
  cmp #192
  bcs dirty_mark_done
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  tax
  lda dirty_bottom
  bmi dirty_mark_done
  cmp #193
  bcc :+
  lda #192
:
  clc
  adc #7
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  tay
dirty_rect_row:
  cpx #96
  bcs dirty_mark_done
  cpx #0
  lda dirty_left
  cmp $0120,x
  bcs :+
  sta $0120,x
:
  lda dirty_right
  cmp $0122,x
  bcc :+
  sta $0122,x
:
  inx
  inx
  inx
  inx
  tya
  sta dirty_bottom
  txa
  cmp dirty_bottom
  bcc dirty_rect_row
dirty_mark_done:
  rts

sa1_prepare_transfer:
  rep #$30
  stz $0118
  stz $011a
  lda #$0800
  sta transferptr
  sep #$20
  lda #$43
  sta transferptr+2
  rep #$20
  ldx #0
  ldy #0
transfer_row:
  lda $0120,x
  pha
  lda $0116
  cmp #3
  pla
  bcc transfer_left
  cmp f:$430400,x
  bcc :+
  lda f:$430400,x
:
transfer_left:
  sta dirty_left
  lda $0122,x
  pha
  lda $0116
  cmp #3
  pla
  bcc transfer_right
  cmp f:$430402,x
  bcs :+
  lda f:$430402,x
:
transfer_right:
  sta dirty_right
  lda $0120,x
  sta f:$430400,x
  lda $0122,x
  sta f:$430402,x
  lda dirty_right
  sec
  sbc dirty_left
  beq transfer_next
  bmi transfer_next
  asl
  asl
  asl
  sta [transferptr],y
  clc
  adc $0118
  sta $0118
  txa
  xba
  clc
  adc dirty_left
  ; X=4*tileY: X<<8=1024*tileY。leftByte<<3=32*tileX。
  sta dirty_top
  lda dirty_left
  asl
  asl
  asl
  sta dirty_bottom
  txa
  xba
  clc
  adc dirty_bottom
  iny
  iny
  sta [transferptr],y
  lsr
  iny
  iny
  sta [transferptr],y
  iny
  iny
  inc $011a
transfer_next:
  inx
  inx
  inx
  inx
  cpx #96
  jne transfer_row
  rtl
