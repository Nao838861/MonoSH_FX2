.setcpu "65816"
.smart
.macpack longbranch
.export fx_is_obj, fx_build_obj, fx_latch_obj, fx_upload_obj
.export fx_obj_upload_done
.export fx_obj_build_done
.export fx_obj_next, fx_obj_present, fx_obj_count, fx_obj_present_count, fx_obj_overflow
.import _fx_draw, _fx_draw_count, _monosh_runtime_frame_counter
.ifdef FX_FAST_OBJ
.segment "ZEROPAGE"
obj_tp: .res 2
obj_layout: .res 2
obj_xy: .res 2
obj_attr: .res 2
.endif
.segment "BSS"
fx_obj_next: .res 68
fx_obj_present: .res 68
fx_obj_count: .res 2
fx_obj_present_count: .res 2
fx_obj_overflow: .res 2
record: .res 2
kind: .res 2
left: .res 2
top: .res 2
flags: .res 2
tile_pointer: .res 2
part: .res 2
px: .res 2
py: .res 2
tile: .res 2
attribute: .res 2
work: .res 2
.segment "CODE"
.a16
.i16
; X=FxDrawのbyte offset。A=0:FX、1:自機、2:自弾。Xを保存する。
fx_is_obj:
  lda _fx_draw+8,x
  and #$ff00
  cmp #$0200
  bne no_obj
  lda _fx_draw+6,x
  and #$ff
  cmp #10
  beq bullet
  cmp #9
  beq player
  cmp #15
  bcc no_obj
  cmp #31
  bcs no_obj
player:
  lda _fx_draw+4,x
  cmp #$3020
  bne no_obj
  lda #1
  rts
bullet:
  lda _fx_draw+4,x
  and #$ff
  beq no_obj
  cmp #17
  bcs no_obj
  sta work
  lda _fx_draw+4,x
  xba
  and #$ff
  cmp work
  bne no_obj
  lda #2
  rts
no_obj:
  lda #0
  rts

fx_build_obj:
  php
  rep #$30
  stz fx_obj_count
  stz fx_obj_overflow
  ldx #0
  lda #$f000
hide:
  sta fx_obj_next,x
  stz fx_obj_next+2,x
  inx
  inx
  inx
  inx
  cpx #64
  bcc hide
  stz fx_obj_next+64
  stz fx_obj_next+66
  lda _fx_draw_count
  and #$ff
  sta work
  asl
  asl
  clc
  adc work
  asl
  sta record
next_record:
  lda record
  jeq done
  sec
  sbc #10
  sta record
  tax
  jsr fx_is_obj
  jeq next_record
  sta kind
  lda _fx_draw+7,x
  and #$ff
  sta flags
  and #$80
  beq :+
  lda _monosh_runtime_frame_counter
  and #1
  jne next_record
:
  lda _fx_draw+4,x
  and #$ff
  lsr
  sta work
  lda _fx_draw,x
  sec
  sbc work
  sta left
  lda _fx_draw+4,x
  xba
  and #$ff
  sta work
  lda _fx_draw+2,x
  sec
  sbc work
  sec
  sbc #8                    ; FX top=bottom-height-20、BG2 V=-13、OBJ pipeline+1。
  sta top
  lda kind
  cmp #2
  jeq single_bullet
  lda _fx_draw+6,x
  and #$ff
  sta work
  asl
  clc
  adc work
  asl
  asl                       ; asset*6*2
  clc
  adc #player_tiles
  sta tile_pointer
.ifdef FX_FAST_OBJ
  ; 全体が画面内なら6個すべてを出す。各partのclip/flip/attribute再計算を省く。
  lda left
  cmp #225
  bcs player_slow
  lda top
  cmp #177
  bcs player_slow
  lda fx_obj_count
  cmp #11
  bcs player_slow
  jsr player_fast
  jmp next_record
player_slow:
.endif
  stz part
player_part:
  lda part
  and #1
  sta work
  lda flags
  and #$10
  beq :+
  lda work
  eor #1
  sta work
:
  lda work
  asl
  asl
  asl
  asl
  clc
  adc left
  sta px
  lda part
  lsr
  sta work
  lda flags
  and #$20
  beq :+
  lda #2
  sec
  sbc work
  sta work
:
  lda work
  asl
  asl
  asl
  asl
  clc
  adc top
  sta py
  lda part
  asl
  clc
  adc tile_pointer
  tax
  lda a:$0000,x             ; DP addressingではbank 0のROMを読んでしまう。
  sta tile
  jsr emit
  inc part
  lda part
  cmp #6
  bcc player_part
  jmp next_record
single_bullet:
  lda left
  sta px
  lda top
  sta py
  lda _fx_draw+4,x
  and #$ff
  asl
  tax
  lda bullet_tiles,x
  sta tile
  jsr emit
  jmp next_record
done:
fx_obj_build_done:
  plp
  rts
emit:
  lda px
  clc
  adc #16
  jmi invisible
  jeq invisible
  lda px
  cmp #256
  jpl invisible
  lda py
  clc
  adc #16
  jmi invisible
  jeq invisible
  lda py
  cmp #224
  jpl invisible
  lda fx_obj_count
  cmp #16
  bcc :+
  inc fx_obj_overflow
  rts
:
  asl
  asl
  tay
  lda py
  xba
  and #$ff00
  sta work
  lda px
  and #$ff
  ora work
  sta fx_obj_next,y
  lda flags
  and #$30
  asl
  asl
  ora #$30                  ; priority 3、palette 0。
  sta attribute
  lda tile
  xba
  and #1
  ora attribute
  xba
  sta work
  lda tile
  and #$ff
  ora work
  sta fx_obj_next+2,y
  lda px
  and #$100
  beq :+
  lda fx_obj_count
  and #3
  asl
  tax
  lda f:$7f0000+high_masks,x
  sta work
  lda fx_obj_count
  lsr
  lsr
  tax
  sep #$20
  lda fx_obj_next+64,x
  ora work
  sta fx_obj_next+64,x
  rep #$20
:
  inc fx_obj_count
invisible:
  rts

.ifdef FX_FAST_OBJ
player_fast:
  lda tile_pointer
  sta obj_tp
  lda top
  xba
  and #$ff00
  ora left
  sta obj_xy
  lda flags
  and #$30
  lsr
  lsr
  sta work
  asl
  clc
  adc work
  adc #player_offsets
  sta obj_layout
  lda flags
  and #$30
  asl
  asl
  ora #$30
  xba
  sta obj_attr
  lda fx_obj_count
  asl
  asl
  tax
  ldy #0
player_fast_part:
  lda (obj_layout),y
  clc
  adc obj_xy
  sta fx_obj_next,x
  lda (obj_tp),y
  ora obj_attr
  sta fx_obj_next+2,x
  inx
  inx
  inx
  inx
  iny
  iny
  cpy #12
  bcc player_fast_part
  lda fx_obj_count
  clc
  adc #6
  sta fx_obj_count
  rts
.segment "RODATA"
player_offsets:
  .word $0000,$0010,$1000,$1010,$2000,$2010
  .word $0010,$0000,$1010,$1000,$2010,$2000
  .word $2000,$2010,$1000,$1010,$0000,$0010
  .word $2010,$2000,$1010,$1000,$0010,$0000
.segment "CODE"
.endif

; FXが描く世代を、CPUが次世代の表を書き換える前に固定する。
fx_latch_obj:
  php
  rep #$30
  ldx #66
copy:
  lda fx_obj_next,x
  sta fx_obj_present,x
  dex
  dex
  bpl copy
  lda fx_obj_count
  sta fx_obj_present_count
  plp
  rts

; forced blank中に16枠のlow64bytes、対応するhigh4bytesだけ更新。
fx_upload_obj:
  php
  rep #$30
  lda #$0400
  sta f:$004300
  lda #fx_obj_present
  sta f:$004302
  sep #$20
  lda #$7e
  sta f:$004304
  lda #0
  sta f:$002102
  sta f:$002103
  rep #$20
  lda #64
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  lda #0
  sta f:$002102
  lda #1
  sta f:$002103
  rep #$20
  lda #fx_obj_present+64
  sta f:$004302
  lda #4
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
fx_obj_upload_done:
  plp
  rts

high_masks: .word 1,4,16,64
.segment "RODATA"
player_tiles: .incbin "assets/obj_tiles.bin"
bullet_tiles: .incbin "assets/obj_bullets.bin"
