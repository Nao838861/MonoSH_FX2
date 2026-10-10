; 次の仕事を待つ間だけ、転送が終わったraw面を先に消す。
; 共有busyをS-CPUが所有する。履歴は実際のDMA完了後に空へ変える。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dma_try_begin: far, sa1_dma_end: far
.export sa1_idle_clear: far, idle_clear_dma: far, idle_clear_done: far
.segment "GSU"
.a16
.i16
icSlot=$a0
icRemaining=$a2
icHistory=$a4
icHistoryBank=$a6
icDest=$a8
icBank=$aa
icBand=$ac

sa1_idle_clear:
  rep #$30
  lda $0116
  jeq ic_return
  lda $0100
  jne ic_return
  lda $011e
  jne ic_return
  lda f:$432740
  asl
  sta icSlot
  lda #7
  sta icRemaining
ic_slot:
  lda $0100
  jne ic_return
  ldx icSlot
  lda f:$4307a0,x
  jne ic_next_slot
  txa
  ; slot*48 = (slot*2)*24
  asl
  clc
  adc icSlot
  .repeat 4
    asl
  .endrepeat
  clc
  adc #$2000
  sta icHistory
  lda #$43
  sta icHistoryBank
  lda f:ic_slots,x
  and #255
  sta icBank
  lda f:ic_slots,x
  and #$8400
  sta icDest
  stz icBand
  ldy #0
ic_band:
  lda $0100
  jne ic_return
  lda [icHistory],y
  iny
  iny
  cmp [icHistory],y
  bcc ic_nonempty
ic_next_band:
  iny
  iny
  lda icDest
  clc
  adc #1024
  sta icDest
  inc icBand
  lda icBand
  cmp #24
  bcc ic_band
ic_next_slot:
  lda icSlot
  clc
  adc #2
  cmp #14
  bcc :+
  lda #0
:
  sta icSlot
  dec icRemaining
  jne ic_slot
ic_return:
  rtl
ic_nonempty:
  jsl sa1_dma_try_begin
  bcc ic_return
idle_clear_dma:
  ; 03:F000..F3FFはcompiled-groundの零専用領域。
  sep #$20
  lda #$84
  sta $2230
  lda #3
  sta $2234
  rep #$20
  lda #$f000
  sta $2232
  lda #1024
  sta $2238
  lda icDest
  sta $2235
  sep #$20
  lda icBank
  sta $2237
  rep #$20
  lda #0
  sta [icHistory],y
  dey
  dey
  lda #128
  sta [icHistory],y
  jsl sa1_dma_end
idle_clear_done:
  rtl
ic_slots:
  .word $0440,$0441,$0442,$8440,$8441,$8442,$8443
