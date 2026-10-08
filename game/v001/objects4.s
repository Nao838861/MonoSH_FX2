.include "assets4/source4.inc"
.if !FX4_COLOR
.include "objects.s"
.else
.setcpu "65816"
.smart
.macpack longbranch
.export fx_is_obj, fx_build_obj, fx_latch_obj, fx_upload_obj
.export fx_obj_upload_done, fx_obj_build_done, fx_obj_dma_bytes
.export fx_obj_next, fx_obj_present, fx_obj_count, fx_obj_present_count, fx_obj_overflow
.import _fx_draw, _fx_draw_count, _monosh_runtime_frame_counter
.import fx4_wait_obj_blank
.segment "BSS"
fx_obj_next: .res 136
fx_obj_present: .res 136
fx_obj_count: .res 2
fx_obj_present_count: .res 2
fx_obj_overflow: .res 2
fx_obj_dma_bytes: .res 2
player4_next: .res 2
.export player4_present
.export player4_upload_bytes
player4_present: .res 2
player4_uploaded: .res 2
player4_upload_bytes: .res 2
player4_x: .res 2
player4_y: .res 2
player4_flags: .res 2
player4_part: .res 2
player4_record: .res 2
player4_position: .res 2
player4_attr: .res 2
.segment "CODE"
.a16
.i16
fx_is_obj:
  lda _fx_draw+8,x
  and #$ff00
  cmp #$0200
  bne no_obj4
  lda _fx_draw+4,x
  cmp #$3020
  bne no_obj4
  lda _fx_draw+6,x
  and #255
  cmp #9
  beq yes_obj4
  cmp #15
  bcc no_obj4
  cmp #31
  bcs no_obj4
yes_obj4:
  lda #1
  rts
no_obj4:
  lda #0
  rts

fx_build_obj:
  php
  rep #$30
  stz fx_obj_count
  stz fx_obj_overflow
  stz player4_next
  ldx #0
hide4:
  lda #$f000
  sta fx_obj_next,x
  stz fx_obj_next+2,x
  inx
  inx
  inx
  inx
  cpx #128
  bcc hide4
  stz fx_obj_next+128
  stz fx_obj_next+130
  stz fx_obj_next+132
  stz fx_obj_next+134
  lda _fx_draw_count
  and #255
  sta player4_record
  asl
  asl
  clc
  adc player4_record
  asl
  sta player4_record
record4:
  lda player4_record
  jeq built4
  sec
  sbc #10
  sta player4_record
  tax
  jsr fx_is_obj
  beq record4
  lda _fx_draw+7,x
  and #255
  sta player4_flags
  bit #$80
  beq :+
  lda _monosh_runtime_frame_counter
  lsr
  and #1
  bne record4
:
  lda _fx_draw,x
  sec
  sbc #16
  sta player4_x
  lda _fx_draw+2,x
  sec
  sbc #56                  ; bottom-height-8、従来OBJと同じ表示位置。
  sta player4_y
  lda _fx_draw+6,x
  and #255
  asl
  tax
  lda player4_offsets,x
  sta player4_next
  stz player4_part
part4:
  lda player4_part
  and #1
  asl
  asl
  asl
  asl
  sta player4_position
  lda player4_flags
  and #$10
  beq :+
  lda #16
  sec
  sbc player4_position
  sta player4_position
:
  lda player4_position
  clc
  adc player4_x
  sta player4_position
  cmp #256
  bcc x_visible4
  cmp #$fff1
  jcc skip_part4
x_visible4:
  lda player4_part
  lsr
  asl
  asl
  asl
  asl
  sta player4_attr
  lda player4_flags
  and #$20
  beq :+
  lda #32
  sec
  sbc player4_attr
  sta player4_attr
:
  lda player4_attr
  clc
  adc player4_y
  cmp #224
  bcc y_visible4
  cmp #$fff1
  jcc skip_part4
y_visible4:
  xba
  and #$ff00
  sta player4_attr
  lda player4_position
  and #255
  ora player4_attr
  pha
  lda player4_part
  asl
  asl
  tax
  pla
  sta fx_obj_next,x
  lda player4_flags
  and #$30
  asl
  asl
  ora #$30                 ; tile64、専用palette0、OBJ priority3。
  xba
  sta player4_attr
  lda player4_part
  asl
  clc
  adc #64
  ora player4_attr
  sta fx_obj_next+2,x
  lda player4_position
  and #$100
  beq skip_part4
  lda player4_part
  asl
  tax
  lda player4_high_masks,x
  ora fx_obj_next+128
  sta fx_obj_next+128
skip_part4:
  inc player4_part
  lda player4_part
  cmp #6
  jcc part4
  lda #6
  sta fx_obj_count
built4:
fx_obj_build_done:
  plp
  rts

fx_latch_obj:
  php
  rep #$30
  ldx #134
latch4:
  lda fx_obj_next,x
  sta fx_obj_present,x
  dex
  dex
  bpl latch4
  lda fx_obj_count
  sta fx_obj_present_count
  lda player4_next
  sta player4_present
  stz player4_upload_bytes
  beq latched4
  cmp player4_uploaded
  beq latched4
  lda #896
  sta player4_upload_bytes
latched4:
  plp
  rts

fx_upload_obj:
  php
  rep #$30
  lda #32
  sta fx_obj_dma_bytes
  lda player4_present
  beq oam4
  cmp player4_uploaded
  beq oam4
  pha
  sep #$20
  jsr fx4_wait_obj_blank
  rep #$20
  pla
  sta player4_uploaded
  sta f:$004302
  lda #$1801
  sta f:$004300
  lda #$6400               ; VRAM byte C800、BG1が参照しない二つ目のmap領域。
  sta f:$002116
  lda #896
  sta f:$004305
  sep #$20
  lda #$5f
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
  lda #928
  sta fx_obj_dma_bytes
oam4:
  lda #$0400
  sta f:$004300
  lda #fx_obj_present
  sta f:$004302
  lda #24
  sta f:$004305
  sep #$20
  lda #$7e
  sta f:$004304
  lda #0
  sta f:$002102
  sta f:$002103
  lda #1
  sta f:$00420b
  lda #0
  sta f:$002102
  lda #1
  sta f:$002103
  rep #$20
  lda #fx_obj_present+128
  sta f:$004302
  lda #8
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
fx_obj_upload_done:
  plp
  rts
.segment "RODATA"
player4_high_masks: .word 1,4,16,64,256,1024
.include "assets4/player_obj.inc"
.endif
