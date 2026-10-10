; 全sprite再描画時の履歴。raw三面は再利用する旧画像だけ消す。
; VRAM二面には新画像と同じ面の二世代前の占有範囲だけを送る。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_occupancy_capture: far
.segment "BOOT"
ocCurrent=$e0
ocTwo=$e4
ocLeft=$e8
ocRight=$ea
ocIndex=$ec
sa1_occupancy_capture:
  rep #$30
  lda $0116
  cmp #1
  bne oc_ready
  ldx #0
oc_initialize:
  lda #128
  sta f:$436000,x
  sta f:$436060,x
  sta f:$4360c0,x
  lda #0
  sta f:$436002,x
  sta f:$436062,x
  sta f:$4360c2,x
  inx
  inx
  inx
  inx
  cpx #96
  bcc oc_initialize
  lda #0
  sta f:$436740
oc_ready:
  lda f:$436740
  sta ocIndex
  jsr oc_address
  sta ocCurrent
  lda ocIndex
  inc
  cmp #3
  bcc :+
  lda #0
:
  sta f:$436740
  jsr oc_address
  sta ocTwo
  sep #$20
  lda #$43
  sta ocCurrent+2
  sta ocTwo+2
  rep #$20
  ldx #0
  ldy #0
oc_band:
  lda $0120,x
  sta ocLeft
  lda $0122,x
  sta ocRight
  lda [ocCurrent],y
  sta $0120,x
  lda ocLeft
  sta [ocCurrent],y
  lda [ocTwo],y
  cmp ocLeft
  bcc :+
  lda ocLeft
:
  sta f:$4304c0,x
  iny
  iny
  lda [ocCurrent],y
  sta $0122,x
  lda ocRight
  sta [ocCurrent],y
  lda [ocTwo],y
  cmp ocRight
  bcs :+
  lda ocRight
:
  sta f:$4304c2,x
  iny
  iny
  inx
  inx
  inx
  inx
  cpx #96
  bcc oc_band
  rtl
oc_address:
  ; 6000 + index*96
  .repeat 5
    asl
  .endrepeat
  sta ocLeft
  asl
  clc
  adc ocLeft
  adc #$6000
  rts
