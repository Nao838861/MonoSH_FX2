; 遠景・近景の水平位置が変わった時だけ、16x256の合成stripを作る。
; 8世代の2KB stripをBW43:8000..BFFFへ保持し、最大5面のmetadataと対応する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dma_begin: far, sa1_dma_end: far, sa1_near_row: far
.export sa1_background_cache: far
.export sa1_background_initialize: far
.segment "BOOT"
bgSlot=$f6
bgOldBank=$f8
bgRow=$e4
bgDest=$e6
bgScroll=$e8
bgFirst=$ea
bgBase=$ec
bgTemp=$f0
sa1_background_cache:
  rep #$30
  lda $0194
  beq bg_cache_build
  lda $0108
  cmp f:$437800
  bne bg_cache_build
  lda $010a
  cmp f:$437802
  bne bg_cache_build
  rtl
bg_cache_build:
  lda $0108
  sta f:$437800
  lda $010a
  sta f:$437802
  inc $0196
  lda $0196
  and #7
  xba
  asl
  asl
  asl
  clc
  adc #$8000
  sta bgSlot
  sta bgDest
  lda $0108
  lsr
  sta bgScroll
  lda $0108
  and #1
  xba
  .repeat 4
    asl
  .endrepeat
  sta bgBase
  stz bgRow
bg_cache_far:
  jsl sa1_dma_begin
  sep #$20
  lda #$84
  sta $2230
  lda #$de
  sta $2234
  rep #$20
  lda #256
  sec
  sbc bgScroll
  cmp #129
  bcc :+
  lda #128
:
  sta bgFirst
  sta $2238
  lda bgRow
  xba
  clc
  adc bgBase
  adc bgScroll
  sta $2232
  lda bgDest
  sta $2235
  sep #$20
  lda #$43
  sta $2237
  rep #$20
  lda #128
  sec
  sbc bgFirst
  beq bg_cache_far_next
  sta $2238
  lda bgRow
  xba
  clc
  adc bgBase
  sta $2232
  lda bgDest
  clc
  adc bgFirst
  sta $2235
  sep #$20
  lda #$43
  sta $2237
  rep #$20
bg_cache_far_next:
  jsl sa1_dma_end
  lda bgDest
  clc
  adc #128
  sta bgDest
  inc bgRow
  lda bgRow
  cmp #14
  bne bg_cache_far
  ; 最後の二行はBG2のtile末尾。画面窓では表示しないが常に0を用意する。
  jsl sa1_dma_begin
  sep #$20
  lda #$84
  sta $2230
  lda #2
  sta $2234
  rep #$20
  lda #$8000
  sta $2232
  lda #256
  sta $2238
  lda bgDest
  sta $2235
  sep #$20
  lda #$43
  sta $2237
  rep #$20
  jsl sa1_dma_end
  lda $0102
  sta bgOldBank
  lda #$43
  sta $0102
  lda bgSlot
  clc
  adc #5*128
  sta bgDest
  stz $d0
  lda #128
  sta $d2
  lda $010a
  and #$1fc
  sta bgScroll
  stz bgRow
bg_cache_near:
  jsl sa1_near_row
  lda bgDest
  clc
  adc #128
  sta bgDest
  inc bgRow
  lda bgRow
  cmp #9
  bne bg_cache_near
  lda bgOldBank
  sta $0102
  lda bgSlot
  sta $0194
  rtl

sa1_background_initialize:
  rep #$30
  stz $0194
  stz $0196
  ldx #1022
bg_initialize_zero:
  stz $0300,x
  dex
  dex
  bpl bg_initialize_zero
  lda #$40
  sta bgOldBank
bg_initialize_bank:
  stz bgSlot
bg_initialize_block:
  jsl sa1_dma_begin
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda #1024
  sta $2238
  lda #$0300
  sta $2232
  lda bgSlot
  sta $2235
  sep #$20
  lda bgOldBank
  sta $2237
  rep #$20
  jsl sa1_dma_end
  lda bgSlot
  clc
  adc #1024
  sta bgSlot
  cmp #$6000
  bcc bg_initialize_block
  inc bgOldBank
  lda bgOldBank
  cmp #$43
  bcc bg_initialize_bank
  rtl
