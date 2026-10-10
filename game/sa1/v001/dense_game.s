; 非表示の先頭8行を余白として、不透明タイルを同じBW-RAM面の先頭へ詰める。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_dense_prepare: far, sa1_dense_done: far
.import sa1_dma_begin: far, sa1_dma_end: far
.import __DENSEJIT_LOAD__, __DENSEJIT_SIZE__
.segment "GSU"
dBase=$a0
dBank=$a2
dSource=$a4
dMap=$a8
dOut=$ac
dBand=$ae
dBits=$b0
dColumn=$b4
dTile=$b6
dMapEntry=$b8
dMapCount=$ba
dMapActive=$bc
dMapDesc=$be
dMapBytes=$c0
dSend=$c2
dCurrent=$c4

sa1_dense_prepare:
  rep #$30
  lda $019a
  sta dBase
  lda $0102
  and #255
  sta dBank
  jsl sa1_dma_begin
  lda #__DENSEJIT_SIZE__
  sta $2238
  lda #.loword(__DENSEJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__DENSEJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  lda #1472
  sta $2238
  lda #.loword(dense_empty_map)
  sta $2232
  sep #$20
  lda #^dense_empty_map
  sta $2234
  lda #$84
  sta $2230
  rep #$20
  lda dBase
  clc
  adc #$6040
  sta $2235
  sep #$20
  lda dBank
  sta $2237
  rep #$20
  jsl sa1_dma_end
  jml dense_entry
.segment "GSU"
dense_empty_map:
.repeat 736
  .word $2420
.endrepeat
.segment "DENSEJIT"
dense_entry:
  lda $0116
  cmp #1
  bne dense_initialized
  ldx #0
  lda #0
dense_initialize:
  sta f:$430700,x
  inx
  inx
  cpx #48
  bcc dense_initialize
dense_initialized:
  lda dBank
  sta dSource+2
  sta dMap+2
  phb
  sep #$20
  lda dBank
  pha
  plb
  rep #$20
  lda dBase
  clc
  adc #$6040
  sta dMap
  lda #32
  sta dOut
  sta dTile
  lda #1
  sta dBand
  sta dMapCount
  stz dMapActive
  stz dMapBytes
dense_band:
  lda dBand
  asl
  asl
  tax
  lda f:$432800,x
  sta dBits
  lda f:$432802,x
  sta dBits+2
  lda dBand
  xba
  asl
  asl
  clc
  adc dBase
  sta dSource
  stz dColumn
  stz dCurrent
dense_tile:
  lda dBits
  ora dBits+2
  jeq dense_tiles_done
  lsr dBits+2
  ror dBits
  bcs dense_tile_present
  inc dColumn
  bra dense_tile
dense_tile_present:
  lda dColumn
  asl
  asl
  clc
  adc dSource
  tax
  lda dOut
  clc
  adc dBase
  tay
  jsl dense_pack_tile
  bcc dense_column_next
  lda #1
  sta dCurrent
  lda dTile
  inc
  sta dTile
  ora #$2400
  sta dMapEntry
  lda dOut
  clc
  adc #32
  sta dOut
  lda dColumn
  asl
  tay
  lda dMapEntry
  sta [dMap],y
dense_column_next:
  inc dColumn
  jmp dense_tile
dense_tiles_done:
  lda dBand
  asl
  tax
  lda f:$430700,x
  ora dCurrent
  sta dSend
  lda dCurrent
  sta f:$430700,x
  lda dSend
  beq dense_map_gap
  lda dMapBytes
  clc
  adc #64
  sta dMapBytes
  lda dMapActive
  beq dense_map_new
  ldx dMapDesc
  lda f:$430800,x
  clc
  adc #64
  sta f:$430800,x
  bra dense_map_next
dense_map_new:
  inc dMapActive
  lda dMapCount
  asl
  sta dMapDesc
  asl
  clc
  adc dMapDesc
  sta dMapDesc
  tax
  lda #64
  sta f:$430800,x
  lda dMap
  sta f:$430802,x
  lda dBand
  dec
  .repeat 5
    asl
  .endrepeat
  clc
  adc #$6020
  sta f:$430804,x
  inc dMapCount
  bra dense_map_next
dense_map_gap:
  stz dMapActive
dense_map_next:
  lda dMap
  clc
  adc #64
  sta dMap
  inc dBand
  lda dBand
  cmp #24
  jne dense_band
  ; 透明文字を先頭に置く。次回再利用時には詰め直した範囲も消す。
  lda dBase
  sta dSource
  lda #0
  ldy #0
dense_zero:
  sta [dSource],y
  iny
  iny
  cpy #32
  bcc dense_zero
  lda f:$432740
  bne :+
  lda #7
:
  dec
  .repeat 5
    asl
  .endrepeat
  sta dSource
  asl
  clc
  adc dSource
  tax
  lda dOut
  clc
  adc #1023
  xba
  and #$00fc
  sta dBand
dense_history:
  lda #0
  sta f:$432000,x
  lda #128
  sta f:$432002,x
  inx
  inx
  inx
  inx
  dec dBand
  dec dBand
  dec dBand
  dec dBand
  bne dense_history
  lda dOut
  sta f:$430800
  clc
  adc dMapBytes
  sta f:$000118
  lda dMapCount
  sta f:$00011a
  lda dBase
  sta f:$430802
  lda #512
  sta f:$430804
sa1_dense_done:
  plb
  rtl

dense_pack_tile:
  .repeat 4, I
  lda a:$0000+(I/2)*128+(I&1)*2,x
  bne dense_copy_tile
  .endrepeat
  .repeat 12, I
  ora a:$0000+((I+4)/2)*128+((I+4)&1)*2,x
  .endrepeat
  bne dense_copy_tile
  clc
  rtl
dense_copy_tile:
  .repeat 16, I
  lda a:$0000+(I/2)*128+(I&1)*2,x
  sta a:$0000+I*2,y
  .endrepeat
  sec
  rtl
