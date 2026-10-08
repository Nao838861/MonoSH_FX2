.setcpu "65816"
.smart
.ifdef FX_SMOOTH_DEPTH
.export fx_em1_open_sizes, _fx_open_size
.segment "CODE"
.a8
.i8
; C参照経路：fastcallのA=Z、X=pose(1..5)。戻りA/X=幅/高さ。
; CODEと一緒に7Fへコピーした表なので、GSU稼働中も読める。
_fx_open_size:
  php
  rep #$30
  and #$ff
  asl
  sta $0390
  asl
  asl
  clc
  adc $0390
  sta $0390
  txa
  and #$ff
  dec
  asl
  clc
  adc $0390
  tax
  lda f:$7f0000+fx_em1_open_sizes,x
  pha
  xba
  and #$ff
  tax
  pla
  plp
  rts
fx_em1_open_sizes:
  .incbin "em1_open_sizes.bin"
.endif
