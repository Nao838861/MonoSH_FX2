; 256pxの行を越える描画が隣の行へ書く部分だけを保存・復元する。
; 対象スプライトは画面幅未満なので、自身の可視画素と保存領域は重ならない。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_edge_save: far, sa1_edge_restore: far
.segment "BOOT"
edgeWidth=$c4
edgeOffset=$c6
edgeFirst=$c8
edgeRows=$ca
edgeCursor=$cc
edgeRemaining=$ce
edgeSourceBank=$d8
edgeDestBank=$da
sa1_edge_save:
  rep #$30
  stz edgeWidth
  lda $38
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
  bra edge_rows
edge_right:
  clc
  adc $34
  cmp #257
  jcc edge_return
  sec
  sbc #255
  lsr
  sta edgeWidth
  stz edgeOffset
edge_rows:
  lda $3a
  dec
  bpl :+
  lda #0
:
  sta edgeFirst
  lda $3a
  clc
  adc $36
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
  lda #$40
  sta edgeSourceBank
  lda #$42
  sta edgeDestBank
  bra edge_copy
sa1_edge_restore:
  rep #$30
  lda edgeWidth
  beq edge_return
  lda #$42
  sta edgeSourceBank
  lda #$40
  sta edgeDestBank
edge_copy:
  lda edgeFirst
  sta edgeCursor
  lda edgeRows
  sta edgeRemaining
edge_line:
  sep #$20
  lda #$81
  sta $2230
  rep #$20
  lda edgeWidth
  sta $2238
  lda edgeCursor
  sta $2232
  sep #$20
  lda edgeSourceBank
  sta $2234
  rep #$20
  lda #$0700
  sta $2235
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda edgeWidth
  sta $2238
  lda #$0700
  sta $2232
  lda edgeCursor
  sta $2235
  sep #$20
  lda edgeDestBank
  sta $2237
  rep #$20
  lda edgeCursor
  clc
  adc #128
  sta edgeCursor
  dec edgeRemaining
  jne edge_line
edge_return:
  rtl
