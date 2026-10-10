; 描画済みの連続二世代を比較し、同じ64pixelのtileを転送集合から除く。
; rawの割当は7面を巡回するため、直前世代の面はこの時点では再利用されない。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_transfer_mask_prepare: far
.export sa1_pixel_delta: far
.segment "GSU"
pdCurrent=$00
pdPrevious=$04
pdIndex=$08
pdMask=$0a
pdBit=$0c
pdOffset=$0e
sa1_pixel_delta:
  rep #$30
  lda $0118
  cmp #SA1_PIXEL_DELTA_MIN
  jcc pd_return
  lda $019a
  sta pdCurrent
  sta pdPrevious
  lda $0102
  and #255
  sta pdCurrent+2
  cmp #$40
  bne pd_previous_bank
  lda $019a
  cmp #$8400
  beq pd_previous_low
  lda #$8400
  sta pdPrevious
  lda #$43
  bra pd_previous_ready
pd_previous_low:
  lda #$0400
  sta pdPrevious
  lda #$42
  bra pd_previous_ready
pd_previous_bank:
  dec
pd_previous_ready:
  sta pdPrevious+2
  lda #4
  sta pdIndex
pd_byte:
  ldx pdIndex
  lda f:$432900,x
  and #255
  sta pdMask
  jeq pd_next_byte
  txa
  and #$fffc
  xba
  sta pdOffset
  txa
  and #3
  .repeat 5
    asl
  .endrepeat
  clc
  adc pdOffset
  sta pdOffset
  lda #1
  sta pdBit
pd_tile:
  lda pdMask
  and pdBit
  jeq pd_changed
  .repeat 8,R
    lda pdOffset
    clc
    adc #128*R
    tay
    lda [pdCurrent],y
    cmp [pdPrevious],y
    jne pd_changed
    iny
    iny
    lda [pdCurrent],y
    cmp [pdPrevious],y
    jne pd_changed
  .endrepeat
  lda pdBit
  eor #$ffff
  and pdMask
  sta pdMask
pd_changed:
  lda pdOffset
  clc
  adc #4
  sta pdOffset
  asl pdBit
  lda pdBit
  cmp #256
  jcc pd_tile
  ldx pdIndex
  lda pdMask
  sep #$20
  sta f:$432900,x
  rep #$20
pd_next_byte:
  inc pdIndex
  lda pdIndex
  cmp #96
  jcc pd_byte
  jml sa1_transfer_mask_prepare
pd_return:
  rtl
