.setcpu "65816"
.smart
.macpack longbranch
.export _fx_submit
.import _fx_draw, _fx_draw_count
.importzp c_sp
.segment "CODE"
.a8
.i8
; cc65: priority=A、残り9bytes=software stack。戻り時に9bytes解放。
_fx_submit:
  php
  rep #$30
  and #$ff
  sta $01e0
  ldy #7
  lda (c_sp),y
  sta $01e2
  ldy #5
  lda (c_sp),y
  sta $01e4
  ldy #3
  lda (c_sp),y
  sta $01e6               ; height, width
  and #$ff
  jeq done
  lda $01e6
  xba
  and #$ff
  jeq done
  lsr
  clc
  adc $01e2
  jmi done
  lda $01e6
  xba
  and #$ff
  lsr
  sta $01e8
  lda $01e2
  sec
  sbc $01e8
  cmp #256
  jpl done
  lda $01e4
  cmp #21
  jmi done
  lda $01e6
  and #$ff
  sta $01e8
  lda $01e4
  sec
  sbc $01e8
  cmp #212
  jpl done
  lda _fx_draw_count
  and #$ff
  cmp #64
  bcs done
  asl
  sta $01e8
  asl
  asl
  clc
  adc $01e8
  tax
  lda $01e2
  sta _fx_draw,x
  lda $01e4
  sta _fx_draw+2,x
  lda $01e6
  xba
  sta _fx_draw+4,x       ; width, height
  ldy #1
  lda (c_sp),y
  xba
  sta _fx_draw+6,x       ; asset, flags
  ldy #0
  lda (c_sp),y
  and #$ff
  sta $01e8
  lda $01e0
  xba
  ora $01e8
  sta _fx_draw+8,x       ; Z, priority
  sep #$20
  inc _fx_draw_count
  rep #$20
done:
  lda c_sp
  clc
  adc #9
  sta c_sp
  plp
  rts
