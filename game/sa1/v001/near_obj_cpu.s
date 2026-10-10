; 512水平位置のOBJ記述子をROMへ保持し、Yだけ実際の地面位置へ合わせる。
.setcpu "65816"
.smart
.macpack longbranch
.export pipe_near_build, pipe_near_select, pipe_near_present
.export pipe_near_prepare_next, pipe_near_prepared
.import pipe_records, pipe_record_offset, pipe_main_offset
.import pipe_status, pipe_next_slot, pipe_write_slot
.import _fx_far_u_acc, _monosh_ground_offset, fx_obj_next, fx_upload_ground
.segment "COLORBSS"
pipe_near_frames: .res 288*8
.segment "ZEROPAGE"
near_pointer: .res 2
.segment "BSS"
near_destination: .res 2
near_source: .res 2
near_bank: .res 2
near_high: .res 2
near_y: .res 2
pipe_near_present: .res 2
pipe_near_prepared: .res 2
.segment "CODE"
; 次の絵のOAMと地面色は、SA-1が現在の絵を描いている間に作っておく。
pipe_near_prepare_next:
  rep #$30
  lda pipe_next_slot
  asl
  tax
  lda pipe_status,x
  bne near_prepare_done
  lda pipe_next_slot
  .repeat 9
    asl
  .endrepeat
  sta pipe_main_offset
  tax
  lda _fx_far_u_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta pipe_records+12,x
  lda _monosh_ground_offset
  and #255
  sta pipe_records+14,x
  lda fx_obj_next+128
  sta pipe_records+192,x
  txa
  clc
  adc #pipe_records+64
  tay
  ldx #fx_obj_next
  lda #23
  mvn #$7e,#$7e
  jsr pipe_near_build
  php
  sei
  jsr fx_upload_ground
  plp
  lda pipe_next_slot
  inc
  sta pipe_near_prepared
  lda pipe_write_slot
  .repeat 9
    asl
  .endrepeat
  sta pipe_main_offset
near_prepare_done:
  rts

pipe_near_build:
  rep #$30
  lda pipe_main_offset
  lsr
  sta near_destination
  lsr
  lsr
  lsr
  clc
  adc near_destination
  adc #pipe_near_frames
  sta near_destination
  lda pipe_main_offset
  clc
  adc #pipe_records+192
  tax
  lda a:$0000,x
  sta near_high
  lda pipe_main_offset
  clc
  adc #pipe_records+64
  tax
  ldy near_destination
  lda #23
  mvn #$7e,#$7e
  ldx pipe_main_offset
  lda pipe_records+12,x
  and #255
  xba
  sta near_source
  lda pipe_records+12,x
  xba
  and #1
  beq near_first_bank
  lda #$de
  bra near_bank_ready
near_first_bank:
  lda #$c0
near_bank_ready:
  sta near_bank
  lda pipe_records+14,x
  clc
  adc #95
  sta near_y
  ; channel0とWRAM portの設定・DMAだけをIRQから保護する。
  php
  sei
  lda near_destination
  clc
  adc #24
  sta f:$002181
  lda #$8000
  sta f:$004300
  lda near_source
  sta f:$004302
  lda #216
  sta f:$004305
  sep #$20
  lda #0
  sta f:$002183
  lda near_bank
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
  lda near_destination
  clc
  adc #256
  sta f:$002181
  lda near_source
  clc
  adc #216
  sta f:$004302
  lda #32
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  plp
  lda near_destination
  sta near_pointer
  ldy #256
  lda (near_pointer),y
  ora near_high
  sta (near_pointer),y
  lda near_y
  cmp #224
  bcc :+
  lda #240
:
  sep #$20
  ldy #25
near_fill_y_first:
  sta (near_pointer),y
  iny
  iny
  iny
  iny
  cpy #133
  bcc near_fill_y_first
  rep #$20
  ldx pipe_main_offset
  lda pipe_records+12,x
  and #7
  bne :+
  sep #$20
  lda #240
  ldy #129
  sta (near_pointer),y
  rep #$20
:
  lda near_y
  clc
  adc #8
  cmp #224
  bcc :+
  lda #240
:
  sep #$20
  ldy #133
near_fill_y_second:
  sta (near_pointer),y
  iny
  iny
  iny
  iny
  cpy #241
  bcc near_fill_y_second
  rep #$20
  ldx pipe_main_offset
  lda pipe_records+12,x
  and #7
  bne :+
  sep #$20
  lda #240
  ldy #237
  sta (near_pointer),y
  rep #$20
:
  ldy #240
near_hide_tail:
  lda #$f000
  sta (near_pointer),y
  iny
  iny
  lda #0
  sta (near_pointer),y
  iny
  iny
  cpy #256
  bcc near_hide_tail
  rts
pipe_near_select:
  rep #$30
  lda pipe_record_offset
  lsr
  sta pipe_near_present
  lsr
  lsr
  lsr
  clc
  adc pipe_near_present
  adc #pipe_near_frames
  sta pipe_near_present
  rts
