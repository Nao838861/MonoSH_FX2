.setcpu "65816"
.smart
.export _fx_build_ground, _fx_ground_native, ground_done, ground_empty, fx_upload_ground
.import _fx_ground_vptr, _fx_ground_c1ptr, _fx_ground_c3ptr
.import _fx_ground_horizon, _monosh_ground_offset, _fx_ground_phase
.import _fx_far_u_acc, _fx_far_d_acc, _fx_ground_far_xptr
.import _fx_ground_hptr, _fx_ground_world_phase, _fx_ground_palette_record
.import _fx_ground_color1, _fx_ground_color3, _fx_ground_horizontal, _fx_ground_far_x
.import _fx_ground_far_y
.segment "ZEROPAGE"
fp: .res 2
hp: .res 2
hv: .res 2
.segment "BSS"
ground_slot: .res 2
.segment "CODE"
.a8
.i8
_fx_build_ground:
  php
  rep #$30
  lda ground_slot
  inc
  cmp #3
  bcc :+
  lda #0
:
  sta ground_slot
  asl
  tax
  lda f:$7f0000+color1_pointers,x
  sta _fx_ground_c1ptr
  lda f:$7f0000+color3_pointers,x
  sta _fx_ground_c3ptr
  lda f:$7f0000+horizontal_pointers,x
  sta _fx_ground_hptr
  lda f:$7f0000+far_pointers,x
  sta _fx_ground_far_xptr
  lda _monosh_ground_offset
  and #$ff
  sta $0120
  clc
  adc #111
  sta _fx_ground_horizon
  lda #14
  sec
  sbc $0120
  sta _fx_ground_far_y
  plp
  jmp _fx_ground_native
_fx_ground_native:
  php
  rep #$30
  lda _monosh_ground_offset
  and #$ff
  sta $0120
  asl
  tax
  lda f:$7f0000+ground_scroll_offsets,x
  clc
  adc #ground_scroll_data
  sta _fx_ground_vptr
  lda f:$7f0000+ground_horizontal_run_offsets,x
  clc
  adc #ground_horizontal_runs
  sta $013c
  lda $0120
  asl
  asl
  asl
  sec
  sbc $0120
  asl
  clc
  adc _fx_ground_phase
  and #$03ff
  sta _fx_ground_palette_record
  lda _fx_ground_far_xptr
  sta fp
  lda _fx_far_u_acc
  .repeat 7
    lsr
  .endrepeat
  and #$ff
  sta $0134
  lda $0120
  clc
  adc #102
  ldy #0
  cmp #128
  bcc far_tail
  pha
  lda #127
  jsr far_run
  pla
  sec
  sbc #127
far_tail:
  jsr far_run
  lda _fx_far_d_acc
  .repeat 7
    lsr
  .endrepeat
  and #$ff
  sta $0134
  lda #2
  jsr far_run
  sep #$20
  lda #0
  sta (fp),y
  rep #$20
  lda _fx_ground_world_phase
  and #$ff
  asl
  tax
  lda f:$7f0000+ground_horizontal_offsets,x
  clc
  adc #ground_horizontal_values
  sta hv
  lda _fx_ground_hptr
  sta hp
  ldy #0
  lda _fx_ground_horizon
  sec
  sbc #7
  cmp #128
  bcc horizontal_tail
  pha
  lda #127
  jsr horizontal_run
  pla
  sec
  sbc #127
horizontal_tail:
  jsr horizontal_run
  sty $013e
  ldx $013c
  lda #0                    ; TAYが16bitを受け取るのでBも0にする。
  sep #$20
row:
  lda f:$7e0000,x
  beq horizontal_done
  sta (hp),y
  iny
  sty $013e
  lda f:$7e0001,x
  tay
  lda (hv),y
  ldy $013e
  sta (hp),y
  iny
  lda #0
  sta (hp),y
  iny
  sty $013e
  inx
  inx
  bra row
horizontal_done:
  lda #0
  sta (hp),y
ground_done:
  plp
  rts
horizontal_run:
  sep #$20
  sta (hp),y
  rep #$20
  iny
  lda #128
  sta (hp),y
  iny
  iny
  rts
far_run:
  sep #$20
  sta (fp),y
  rep #$20
  iny
  lda $0134
  sta (fp),y
  iny
  iny
  rts

; GSU STOP中にだけROMの色テーブルをWRAMへ移す。次画像準備はROMに触れない。
fx_upload_ground:
  php
  rep #$30
  lda #$8000
  sta f:$004300
  lda _fx_ground_palette_record
  and #$ff
  xba
  sta f:$004302
  lda _fx_ground_palette_record
  xba
  and #$ff
  clc
  adc #$5a
  sep #$20
  sta f:$004304
  lda #0
  sta f:$002183
  rep #$20
  lda _fx_ground_c1ptr
  sta f:$002181
  lda #128
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  lda _fx_ground_c3ptr
  sta f:$002181
  lda #128
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  plp
  rts

ground_empty: .byte 0
color1_pointers: .word _fx_ground_color1, _fx_ground_color1+150, _fx_ground_color1+300
color3_pointers: .word _fx_ground_color3, _fx_ground_color3+150, _fx_ground_color3+300
horizontal_pointers: .word _fx_ground_horizontal, _fx_ground_horizontal+210, _fx_ground_horizontal+420
far_pointers: .word _fx_ground_far_x, _fx_ground_far_x+10, _fx_ground_far_x+20
ground_scroll_offsets: .incbin "assets/ground_scroll_offsets.bin"
ground_horizontal_run_offsets: .incbin "assets/ground_horizontal_run_offsets.bin"
ground_scroll_data: .incbin "assets/ground_scroll.bin"
.segment "RODATA"
ground_horizontal_runs: .incbin "assets/ground_horizontal_runs.bin"
.segment "CODE"
ground_horizontal_offsets: .incbin "assets/ground_horizontal_offsets.bin"
.segment "RODATA"
ground_horizontal_values: .incbin "assets/ground_horizontal.bin"
.repeat 4,I
  .segment .sprintf("PAL%02X",$5A+I)
  .incbin .sprintf("assets/palette%02x.bin",$5A+I)
.endrepeat
