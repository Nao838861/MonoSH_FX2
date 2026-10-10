.setcpu "65816"
.smart
.export sa1_dirty_iram_load: far
.import __DIRTYJIT_LOAD__, __DIRTYJIT_SIZE__, sa1_tile_masks
.import sa1_dma_begin: far, sa1_dma_end: far
.segment "GSU"
sa1_dirty_iram_load:
  rep #$30
  jsl sa1_dma_begin
  lda #__DIRTYJIT_SIZE__
  sta $2238
  lda #.loword(__DIRTYJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__DIRTYJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  lda #132
  sta $2238
  lda #sa1_tile_masks
  sta $2232
  sep #$20
  stz $2234
  rep #$20
  lda #$0600
  sta $2235
  jml sa1_dma_end
