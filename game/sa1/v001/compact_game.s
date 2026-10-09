; 512px幅の描画用余白から256px幅へ差分行だけを集める。
; SA-1のキャラクタ変換DMAが扱える最大幅は32タイルなので、直接512pxを渡さない。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_compact: far
.segment "BOOT"
compactTile=$a0
compactWidth=$a2
compactSource=$a4
compactDest=$a6
compactLines=$a8
sa1_compact:
  rep #$30
  stz compactTile
compact_tile:
  lda compactTile
  asl
  asl
  tax
  lda $0122,x
  sec
  sbc $0120,x
  jeq compact_next
  jmi compact_next
  sta compactWidth
  lda compactTile
  xba
  asl
  asl
  clc
  adc $0120,x
  sta compactDest
  lda compactTile
  xba
  asl
  asl
  asl
  clc
  adc #64
  adc $0120,x
  sta compactSource
  lda #8
  sta compactLines
compact_line:
  sep #$20
  lda #$81
  sta $2230
  rep #$20
  lda compactWidth
  sta $2238
  lda compactSource
  sta $2232
  sep #$20
  lda #$40
  sta $2234
  rep #$20
  lda #$0700
  sta $2235
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda compactWidth
  sta $2238
  lda #$0700
  sta $2232
  lda compactDest
  sta $2235
  sep #$20
  lda #$41
  sta $2237
  rep #$20
  lda compactSource
  clc
  adc #256
  sta compactSource
  lda compactDest
  clc
  adc #128
  sta compactDest
  dec compactLines
  bne compact_line
compact_next:
  inc compactTile
  lda compactTile
  cmp #24
  jne compact_tile
  rtl
