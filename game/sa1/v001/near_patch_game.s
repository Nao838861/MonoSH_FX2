; OBJの走査線上限を守る48pxの切れ目だけ、同じ近景をSA-1で補う。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_near_row: far, sa1_dirty_row_rect: far
.export sa1_near_patch: far, sa1_near_patch_bounds: far
.segment "BOOT"
sa1_near_patch_bounds:
  rep #$30
  jsr patch_geometry
  lda $d0
  lsr
  lsr
  asl
  asl
  sta $a8
  lda $d2
  clc
  adc #3
  lsr
  lsr
  asl
  asl
  sta $aa
  lda $010c
  clc
  adc #82
  sta $ac
  clc
  adc #9
  sta $ae
  jsl sa1_dirty_row_rect
  rtl
patch_geometry:
  lda $010a
  and #7
  eor #$ffff
  inc
  clc
  adc #112
  and #$fffc
  lsr
  sta $d0
  lda $010a
  and #7
  eor #$ffff
  inc
  clc
  adc #160+3
  and #$fffc
  lsr
  sta $d2
  rts
sa1_near_patch:
  rep #$30
  lda $010c
  clc
  adc #82
  cmp #192
  bcs patch_done
  .repeat 7
    asl
  .endrepeat
  clc
  adc $019a
  sta $e6
  jsr patch_geometry
  lda $010a
  and #$1fc
  sta $e8
  stz $e4
patch_row:
  jsl sa1_near_row
  lda $e6
  clc
  adc #128
  sta $e6
  sec
  sbc $019a
  cmp #192*128
  bcs patch_done
  inc $e4
  lda $e4
  cmp #9
  bcc patch_row
patch_done:
  rtl
