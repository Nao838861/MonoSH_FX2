; 左端だけのclipは最初の可視wordからROM末尾のRTLまで直接実行する。
; 命令は3Bずつで、各STAのoffsetは単調増加する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_clip_left_tail: far
.segment "BOOT"
clipLow=$a0
clipHigh=$a2
clipMid=$a4
clipStore=$a6
clipStart=$a8
sa1_clip_left_tail:
  rep #$30
  lda $70                       ; cur: rowの最初の不透明word
  jpl clip_unavailable
  lda $ce                       ; coverEnd
  cmp $d2                       ; dirtyR
  jcc clip_left_only
  jeq clip_left_only
clip_unavailable:
  clc
  rtl
clip_left_only:
  lda $84
  cmp $ba
  bne clip_compute
  lda $86
  and #255
  cmp $b8
  bne clip_compute
  lda $70
  cmp $b6
  bne clip_compute
  lda $bc
  sta $07f1
  lda $be
  sta $d6
  jmp clip_entry_bank
clip_compute:
  stz clipLow
  lda $8c                       ; codelen
  sec
  sbc #4
  sta clipHigh
clip_search:
  lda clipLow
  cmp clipHigh
  bcs clip_search_done
  clc
  adc clipHigh
  lsr
  tax
  lda f:clip_align,x
  and #255
  sta clipMid
  tay
clip_next_store:
  sep #$20
  lda [$84],y
  cmp #$9d
  beq clip_check_store
  rep #$20
  iny
  iny
  iny
  bra clip_next_store
clip_check_store:
  rep #$20
  iny
  lda [$84],y
  clc
  adc $70
  inc                            ; wordの右byteが0以上なら可視
  bmi clip_discard_group
  lda clipMid
  sta clipHigh
  bra clip_search
clip_discard_group:
  tya
  clc
  adc #2
  sta clipLow
  bra clip_search
clip_search_done:
  tay
clip_find_store:
  sep #$20
  lda [$84],y
  cmp #$9d
  beq clip_store_found
  rep #$20
  iny
  iny
  iny
  bra clip_find_store
clip_store_found:
  rep #$20
  sty clipStore
  stz $d6                        ; initialA
  dey
  dey
  dey
clip_find_group:
  bmi clip_first_group
  sep #$20
  lda [$84],y
  cmp #$9d
  beq clip_previous_store
  rep #$20
  dey
  dey
  dey
  bra clip_find_group
clip_previous_store:
  rep #$20
  tya
  clc
  adc #3
  bra clip_group_ready
clip_first_group:
  lda #0
clip_group_ready:
  sta clipStart
  cmp clipStore
  bne clip_entry_ready
  ldy clipStore
clip_find_accumulator:
  dey
  dey
  dey
  sep #$20
  lda [$84],y
  cmp #$a9
  bne clip_find_accumulator
  rep #$20
  iny
  lda [$84],y
  sta $d6
clip_entry_ready:
  lda clipStart
  clc
  adc $84
  sta $07f1
  sta $bc
  lda $d6
  sta $be
  lda $70
  sta $b6
  lda $86
  and #255
  sta $b8
  lda $84
  sta $ba
clip_entry_bank:
  sep #$20
  lda $86
  sta $07f3
  rep #$30
  sec
  rtl
clip_align:
.repeat 256,I
  .byte (I/3)*3
.endrepeat
