; GSUの四本のstripをCPUで事前clipし、Q8.8も一度だけ計算する。
; cart $8000,$8D00,$9A00,$A700: count(u16), 24byte commands。
.segment "BSS"
p4_quarter: .res 2
p4_base: .res 2
p4_record: .res 2
p4_count: .res 2
p4_left: .res 2
p4_top: .res 2
p4_width: .res 2
p4_height: .res 2
p4_x: .res 2
p4_y: .res 2
p4_w: .res 2
p4_h: .res 2
p4_sx: .res 2
p4_sy: .res 2
p4_du: .res 2
p4_dv: .res 2
p4_u: .res 2
p4_v: .res 2
p4_meta: .res 2
p4_asset: .res 2
p4_flags: .res 2
p4_aw: .res 2
p4_ah: .res 2
p4_mul_value: .res 2
p4_mul_mask: .res 2
p4_mul_low: .res 2
.segment "RODATA"
dimensions4: .incbin "assets4/dimensions.bin"
.segment "CODE"
.a16
.i16
prepare_commands4:
  php
  rep #$30
  stz p4_quarter
  lda #0
  sta p4_base
p4_next_quarter:
  lda p4_base
  inc
  inc
  tax
  stz p4_record
  stz p4_count
p4_next:
  lda p4_record
  cmp f:$7e1d02
  jcs p4_quarter_done
  tay
  lda _fx_packet+4,y
  and #$ff
  jeq p4_skip
  sta p4_width
  lsr
  sta p4_sx
  lda _fx_packet,y
  sec
  sbc p4_sx
  sta p4_left
  sec
  sbc p4_quarter
  bpl :+
  lda p4_quarter
  bra p4_x_ready
:
  lda p4_left
p4_x_ready:
  sta p4_x
  sec
  sbc p4_left
  sta p4_sx
  lda p4_left
  clc
  adc p4_width
  sec
  sbc p4_quarter
  cmp #256
  bmi :+
  lda #256
:
  clc
  adc p4_quarter
  sec
  sbc p4_x
  jmi p4_skip
  jeq p4_skip
  sta p4_w
  lda _fx_packet+5,y
  and #$ff
  jeq p4_skip
  sta p4_height
  lda _fx_packet+2,y
  sec
  sbc p4_height
  sec
  sbc #20
  sta p4_top
  bpl :+
  lda #0
:
  sta p4_y
  sec
  sbc p4_top
  sta p4_sy
  lda p4_top
  clc
  adc p4_height
  cmp #192
  bmi :+
  lda #192
:
  sec
  sbc p4_y
  jmi p4_skip
  jeq p4_skip
  sta p4_h
  lda _fx_packet+6,y
  and #$ff
  sta p4_asset
  asl
  phx
  tax
  lda f:$7e0000+dimensions4,x
  and #$ff
  sta p4_aw
  lda f:$7e0000+dimensions4+1,x
  and #$ff
  sta p4_ah
  plx
  lda _fx_packet+7,y
  and #$ff
  sta p4_flags
  lda p4_aw
  xba
  sta f:$004204
  sep #$20
  lda p4_width
  sta f:$004206
  rep #$20
  lda p4_x
  sta f:$7e0400,x
  sta f:$7e0408,x
  lda p4_y
  sta f:$7e0402,x
  lda f:$004214
  sta p4_du
  lda p4_ah
  xba
  sta f:$004204
  sep #$20
  lda p4_height
  sta f:$004206
  rep #$20
  lda p4_h
  sta f:$7e040a,x
  lda p4_w
  sta f:$7e040e,x
  lda f:$004214
  sta p4_dv
  lda p4_sx
  xba
  and #$ff00
  sta p4_mul_mask
  lda p4_du
  jsr p4_multiply
  sta p4_u
  lda p4_sy
  xba
  and #$ff00
  sta p4_mul_mask
  lda p4_dv
  jsr p4_multiply
  sta p4_v
  lda p4_flags
  and #$10
  beq p4_no_flip_x
  lda #0
  sec
  sbc p4_du
  sta p4_du
  lda p4_aw
  xba
  dec
  sec
  sbc p4_u
  sta p4_u
p4_no_flip_x:
  lda p4_flags
  and #$20
  beq p4_no_flip_y
  lda #0
  sec
  sbc p4_dv
  sta p4_dv
  lda p4_ah
  xba
  dec
  sec
  sbc p4_v
  sta p4_v
p4_no_flip_y:
  lda p4_asset
  and #1
  beq :+
  lda p4_v
  ora #$8000
  sta p4_v
:
  lda p4_du
  sta f:$7e0404,x
  lda p4_dv
  sta f:$7e0406,x
  lda p4_v
  sta f:$7e040c,x
  lda p4_u
  sta f:$7e0410,x
  lda p4_flags
  and #$30
  asl
  asl
  ora p4_asset
  xba
  sta p4_meta
  lda p4_asset
  lsr
  clc
  adc #$44
  ora p4_meta
  sta f:$7e0412,x
  lda p4_width
  sta f:$7e0414,x
  lda p4_sx
  sta f:$7e0416,x
  txa
  clc
  adc #24
  tax
  inc p4_count
p4_skip:
  lda p4_record
  clc
  adc #10
  sta p4_record
  jmp p4_next
p4_quarter_done:
  ldx p4_base
  lda p4_count
  sta f:$7e0400,x
  plp
  rts

; A(u16) * p4_mul_mask.high(u8) の下位16bit。X/Yを保存する。
p4_multiply:
  sta p4_mul_value
  and #$ff
  ora p4_mul_mask
  sta f:$004202
  nop
  nop
  nop
  nop
  lda f:$004216
  sta p4_mul_low
  lda p4_mul_value
  xba
  and #$ff
  ora p4_mul_mask
  sta f:$004202
  nop
  nop
  nop
  nop
  lda f:$004216
  xba
  and #$ff00
  clc
  adc p4_mul_low
  rts
