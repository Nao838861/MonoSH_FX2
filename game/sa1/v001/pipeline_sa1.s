; S-CPUのキャラクタ変換DMAと描画用DMAを排他する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_dma_begin: far, sa1_dma_end: far, sa1_snapshot: far, sa1_dma_poll: far
.segment "BOOT"
sa1_dma_begin:
  php
  rep #$20
  pha
dma_retry:
  lda #1
  sta $011c
  lda $011e
  beq dma_entered
  jsr dma_yield
  bra dma_retry
dma_entered:
  pla
  plp
  rtl
sa1_dma_end:
  php
  rep #$20
  pha
  stz $011c
  pla
  plp
  rtl
sa1_dma_poll:
  php
  rep #$20
  pha
  lda $011e
  beq poll_done
  jsr dma_yield
poll_done:
  pla
  plp
  rtl
dma_yield:
  sep #$20
  lda #$b1
  sta $2230
  rep #$20
  lda #2
  sta $011c
dma_wait:
  lda $0100
  bne :+
  lda $0104
  beq :+
  stz $0104
  lda #1
  sta $1e
:
  lda $011e
  bne dma_wait
  stz $011c
  rts
sdesc=$a0
sremaining=$a2
swidth=$a4
ssource=$a6
slines=$a8
sa1_snapshot:
  rep #$30
  stz sdesc
  lda $011a
  sta sremaining
snapshot_descriptor:
  lda sremaining
  jeq snapshot_done
  ldx sdesc
  lda f:$430800,x
  lsr
  lsr
  lsr
  sta swidth
  lda f:$430802,x
  and #$03ff
  lsr
  lsr
  lsr
  sta ssource
  lda f:$430802,x
  and #$fc00
  clc
  adc ssource
  sta ssource
  lda #8
  sta slines
snapshot_line:
  jsl sa1_dma_begin
  sep #$20
  lda #$81
  sta $2230
  lda #$40
  sta $2234
  rep #$20
  lda swidth
  sta $2238
  lda ssource
  sta $2232
  lda #$0600
  sta $2235
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda swidth
  sta $2238
  lda #$0600
  sta $2232
  lda ssource
  sta $2235
  sep #$20
  lda $0102
  sta $2237
  jsl sa1_dma_end
  rep #$20
  lda ssource
  clc
  adc #128
  sta ssource
  dec slines
  bne snapshot_line
  lda sdesc
  clc
  adc #6
  sta sdesc
  dec sremaining
  jmp snapshot_descriptor
snapshot_done:
  rtl

.export sa1_fb_read: far, sa1_fb_write: far
.a8
.i16
sa1_fb_read:
  phy
  txy
  lda [$10],y
  ply
  rtl
sa1_fb_write:
  phy
  txy
  sta [$10],y
  ply
  rtl
