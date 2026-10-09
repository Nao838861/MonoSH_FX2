; 画面端から隣の行へはみ出す画素だけをI-RAMへ退避する。
; I-RAM $0600..06ff はrow call chainの$0700..07efと重ならない。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_edge_prepare: far, sa1_edge_save: far, sa1_edge_restore: far
.segment "BOOT"
edgeWidth=$c4
edgeOffset=$c6
edgeFirst=$c8
edgeRows=$ca
edgeCursor=$cc
edgeRemaining=$ce
edgeCache=$d8
edgeChunkLimit=$da
sa1_edge_prepare:
  rep #$30
  stz edgeWidth
  lda $c0
  and #255
  clc
  adc $38
  bpl edge_right
  cmp #$8000
  ror
  eor #$ffff
  inc
  sta edgeWidth
  lda #128
  sec
  sbc edgeWidth
  sta edgeOffset
  bra edge_limit
edge_right:
  lda $c2
  and #255
  clc
  adc $38
  cmp #257
  bcc edge_return
  sec
  sbc #255
  lsr
  sta edgeWidth
  stz edgeOffset
edge_limit:
  lda #256
  ldy #0
edge_divide:
  sec
  sbc edgeWidth
  bcc edge_divided
  iny
  cpy #22
  bcc edge_divide
edge_divided:
  dey
  dey
  sty edgeChunkLimit
edge_return:
  rtl
sa1_edge_save:
  rep #$30
  lda edgeWidth
  beq edge_return
  lda $3a
  clc
  adc $a0                    ; source first row
  dec
  bpl :+
  lda #0
:
  sta edgeFirst
  lda $3a
  clc
  adc $a0
  adc $a8                    ; source row count
  inc
  cmp #193
  bcc :+
  lda #192
:
  sec
  sbc edgeFirst
  sta edgeRows
  lda edgeFirst
  .repeat 7
    asl
  .endrepeat
  clc
  adc edgeOffset
  sta edgeFirst
  sta edgeCursor
  lda edgeRows
  sta edgeRemaining
  lda #$0600
  sta edgeCache
edge_save_line:
  sep #$20
  lda #$81
  sta $2230
  lda #$40
  sta $2234
  rep #$20
  lda edgeWidth
  sta $2238
  lda edgeCursor
  sta $2232
  lda edgeCache
  sta $2235
  jsr edge_next
  bne edge_save_line
  rtl
sa1_edge_restore:
  rep #$30
  lda edgeWidth
  beq edge_return
  lda edgeFirst
  sta edgeCursor
  lda edgeRows
  sta edgeRemaining
  lda #$0600
  sta edgeCache
edge_restore_line:
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda edgeWidth
  sta $2238
  lda edgeCache
  sta $2232
  lda edgeCursor
  sta $2235
  sep #$20
  lda #$40
  sta $2237
  rep #$20
  jsr edge_next
  bne edge_restore_line
  rtl
edge_next:
  lda edgeCache
  clc
  adc edgeWidth
  sta edgeCache
  lda edgeCursor
  clc
  adc #128
  sta edgeCursor
  dec edgeRemaining
  rts
