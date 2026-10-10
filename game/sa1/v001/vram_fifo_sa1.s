; 可変長CHR FIFO。8KiB境界のzero tileを避け、32KiBのBG1窓へ収める。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_fifo_allocate: far, sa1_sparse_direct_finish: far, sparse_direct_overflow: far
.ifndef SA1_PREFIX_DESC_COST
SA1_PREFIX_DESC_COST=64
.endif
.segment "GSU"
fStart=$c0
fHead=$c2
fBase=$c4
fCost=$c6
fCount=$c8
fOrigin=$ca
fSize=$cc
fLimit=$ce
fEnd=$d0
.a16
.i16
sa1_fifo_allocate:
  rep #$30
  lda $0116
  cmp #2
  bcs :+
  lda #0
  sta f:$437e00
  sta f:$437e04
:
  lda $0118
  .repeat 5
    lsr
  .endrepeat
  sta fSize
  cmp #352
  jcs sparse_direct_overflow
  lda f:$437e00
  sta fOrigin
  sta fHead
  stz fCost
  jsr fifo_allocate_span
.ifdef SA1_FIFO_FAST
  lda fEnd
.else
  lda fHead
  cmp fStart
  bcs :+
  clc
  adc #2048
:
.endif
  sec
  sbc fBase
  cmp #1025
  bcc fifo_span_fits
  lda #1505
  sec
  sbc fOrigin
  sta fCost
  stz fHead
  jsr fifo_allocate_span
fifo_span_fits:
  lda fHead
  sta f:$437e00
  lda f:$437e04
  clc
  adc fCost
  sta f:$437e04
  sta $01a6
  lda fCost
  sta $01a4
  lda fBase
  sta $01a2
  lda fStart
  sta $01a0
  lda #1505
  sec
  sbc fBase
  cmp #1024
  bcc :+
  lda #$ffff
  sta fLimit
  rtl
:
  ora #$2400
  sta fLimit
  rtl
fifo_allocate_span:
.ifdef SA1_FIFO_FAST
  jmp fifo_span_fast
.endif
  lda fHead
  bit #255
  bne :+
  inc fHead
  inc fCost
:
  lda fHead
  sta fStart
  and #$ff00
  sta fBase
  lda fSize
  sta fCount
  beq fifo_span_done
fifo_span_tile:
  inc fHead
  inc fCost
  dec fCount
  beq fifo_span_done
  lda fHead
  cmp #1505
  bcc :+
  stz fHead
:
  lda fHead
  bit #255
  bne fifo_span_tile
  inc fHead
  inc fCost
  bra fifo_span_tile
fifo_span_done:
  lda fHead
  cmp #1505
  bcc :+
  stz fHead
:
  rts
.ifdef SA1_FIFO_FAST
fifo_span_fast:
  lda fHead
  bit #255
  bne :+
  inc fHead
  inc fCost
:
  lda fHead
  sta fStart
  and #$ff00
  sta fBase
  clc
  adc #256
  sta fCount
  lda fHead
  clc
  adc fSize
  sta fHead
  ldx #2
fifo_fast_zero:
  lda fCount
  cmp #1505
  bcs fifo_fast_wrap
  cmp fHead
  bcs :+
  inc fHead
:
  lda fCount
  clc
  adc #256
  sta fCount
  dex
  bne fifo_fast_zero
fifo_fast_wrap:
  lda fHead
  cmp #1506
  bcc fifo_fast_no_wrap
  sec
  sbc #1505
  inc
  cmp #257
  bcc :+
  inc
:
  sta fHead
  clc
  adc #2048
  sta fEnd
  lda fHead
  clc
  adc #1505
  bra fifo_fast_cost
fifo_fast_no_wrap:
  sta fEnd
fifo_fast_cost:
  sec
  sbc fStart
  clc
  adc fCost
  sta fCost
  lda fHead
  cmp #1505
  bcc :+
  stz fHead
:
  rts
.endif

oInput=$a0
oEnd=$a2
oOutput=$a4
oDest=$a6
oLength=$a8
oSource=$aa
oTake=$ac
oBoundary=$ae
oMap=$d2
oMapOffset=$d6
oMapCount=$d8
sa1_sparse_direct_finish:
  rep #$30
.ifdef SA1_FIFO_FUSED_MAP
  lda $019a
  clc
  adc #$6040
  sta oMap
  lda $0102
  sta oMap+2
.endif
  lda $011a
  asl
  sta oEnd
  asl
  clc
  adc oEnd
  sta oEnd
  stz oInput
  stz oOutput
  stz $b0
  lda $01a0
  .repeat 4
    asl
  .endrepeat
  sta oDest
  stz $b4
  stz $b6
  lda $019a
  clc
  adc #$6600
  sta $b8
  lda $0102
  sta $ba
fifo_descriptor:
  ldx oInput
  cpx oEnd
  jcs fifo_descriptors_done
.ifdef SA1_FIFO_FAST
  lda f:$434000,x
.else
  lda f:$430800,x
.endif
  sta oLength
.ifdef SA1_FIFO_FAST
  lda f:$434002,x
.else
  lda f:$430802,x
.endif
  sta oSource
.ifdef SA1_FIFO_FUSED_MAP
  lda f:$434004,x
  .repeat 3
    lsr
  .endrepeat
  sec
  sbc #64
  sta oMapOffset
.endif
fifo_piece:
  lda oDest
  cmp #$5e10
  bcc :+
  stz oDest
:
  lda oDest
  bit #$0fff
  bne :+
  clc
  adc #16
  sta oDest
:
  lda oDest
  and #$f000
  clc
  adc #$1000
  cmp #$5e10
  bcc :+
  lda #$5e10
:
  sec
  sbc oDest
  asl
  cmp oLength
  bcc :+
  lda oLength
:
  sta oTake
  jeq sparse_direct_overflow
  ldx oOutput
  cpx #300
  jcs sparse_direct_overflow
.ifdef SA1_FIFO_FAST
  sta f:$430800,x
.else
  sta f:$434000,x
.endif
  lda oSource
.ifdef SA1_FIFO_FAST
  sta f:$430802,x
.else
  sta f:$434002,x
.endif
  lda $01a2
  .repeat 4
    asl
  .endrepeat
  sta oBoundary
  lda oDest
  sec
  sbc oBoundary
  and #$7fff
.ifdef SA1_FIFO_FAST
  sta f:$430804,x
.else
  sta f:$434004,x
.endif
.ifdef SA1_FIFO_FUSED_MAP
  ldy oMapOffset
  .repeat 4
    lsr
  .endrepeat
  ora #$2400
  pha
  lda oTake
  .repeat 5
    lsr
  .endrepeat
  sta oMapCount
  pla
fifo_map_run:
  sta [oMap],y
  inc
  iny
  iny
  dec oMapCount
  bne fifo_map_run
  sty oMapOffset
.endif
  lda oTake
  clc
  adc $b4
  sta $b4
  ldy $b0
  lda $b4
  sta [$b8],y
  iny
  iny
  lda oTake
  .repeat 5
    lsr
  .endrepeat
  sta $be
  lsr
  lsr
  clc
  adc $be
  adc oTake
  adc #SA1_PREFIX_DESC_COST
  adc $b6
  sta $b6
  sta [$b8],y
  iny
  iny
  sty $b0
  lda oTake
  lsr
  clc
  adc oDest
  sta oDest
  lda oSource
  clc
  adc oTake
  sta oSource
  lda oOutput
  clc
  adc #6
  sta oOutput
  lda oLength
  sec
  sbc oTake
  sta oLength
  jne fifo_piece
  lda oInput
  clc
  adc #6
  sta oInput
  jmp fifo_descriptor
fifo_descriptors_done:
.ifndef SA1_FIFO_FAST
  ldx #0
fifo_copy:
  cpx oOutput
  bcs fifo_copy_done
  lda f:$434000,x
  sta f:$430800,x
  inx
  inx
  bra fifo_copy
fifo_copy_done:
.endif
  lda oOutput
  lsr
  tax
  lda f:fifo_div6,x
  and #255
  sta $011a
  rtl
fifo_div6:
  .repeat 151,I
  .byte I/3
  .endrepeat
sparse_direct_overflow:
  stp
