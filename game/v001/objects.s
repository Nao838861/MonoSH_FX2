.setcpu "65816"
.smart
.macpack longbranch
.export fx_is_obj, fx_build_obj, fx_latch_obj, fx_upload_obj
.export fx_obj_upload_done
.export fx_obj_build_done
.export fx_obj_dma_bytes
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
fx_obj_next: .res 136
fx_obj_present: .res 136
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
obj_size: .res 2
bullet_width: .res 2
bullet_height: .res 2
bullet_count: .res 2
last_upload_count: .res 2
fx_obj_dma_bytes: .res 2
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
  cpx #128
  bcc hide
  stz fx_obj_next+128
  stz fx_obj_next+130
  stz fx_obj_next+132
  stz fx_obj_next+134
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
  lda #16
  sta obj_size
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
  cmp #27
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
  lda _fx_draw+4,x
  and #$ff
  sta work
  lda flags
  and #$40                  ; 反射弾には発射直後の大きな輪を使わない。
  beq :+
  lda #7
  sta work
:
  lda work
  asl
  tay
  lda bullet_tiles,y
  clc
  adc #bullet_tiles+34
  sta tile_pointer
  tay
  lda a:$0000,y
  and #$ff
  sta bullet_width
  lsr
  sta work
  lda _fx_draw,x
  sec
  sbc work
  sta left
  lda a:$0000,y
  xba
  and #$ff
  sta bullet_height
  lsr
  sta work
  lda _fx_draw+4,x
  xba
  and #$ff
  lsr
  clc
  adc work
  sta work
  lda _fx_draw+2,x
  sec
  sbc work
  sec
  sbc #8
  sta top
  lda a:$0002,y
  and #$ff
  sta bullet_count
  lda tile_pointer
  clc
  adc #4
  sta tile_pointer
  stz part
bullet_part:
  lda part
  asl
  asl
  clc
  adc tile_pointer
  tax
  lda a:$0002,x
  sta tile
  lda #16
  bit tile
  bpl :+
  lda #32
:
  sta obj_size
  lda a:$0000,x
  and #$ff
  sta work
  lda flags
  and #$10
  beq :+
  lda bullet_width
  sec
  sbc work
  sec
  sbc obj_size
  sta work
:
  lda left
  clc
  adc work
  sta px
  lda a:$0000,x
  xba
  and #$ff
  sta work
  lda flags
  and #$20
  beq :+
  lda bullet_height
  sec
  sbc work
  sec
  sbc obj_size
  sta work
:
  lda top
  clc
  adc work
  sta py
  jsr emit
  inc part
  lda part
  cmp bullet_count
  jcc bullet_part
  jmp next_record
done:
fx_obj_build_done:
  plp
  rts
emit:
  lda px
  clc
  adc obj_size
  jmi invisible
  jeq invisible
  lda px
  cmp #256
  jpl invisible
  lda py
  clc
  adc obj_size
  jmi invisible
  jeq invisible
  lda py
  cmp #224
  jpl invisible
  lda fx_obj_count
  cmp #32
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
  lda kind
  cmp #2
  bne :+
  lda attribute
  ora #2                    ; 自弾は独立した水色palette 1。
  sta attribute
:
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
  xba
  and #1
  sta work
  lda obj_size
  cmp #32
  bne :+
  lda work
  ora #2
  sta work
:
  lda fx_obj_count
  and #3
  tay
  lda work
shift_high:
  cpy #0
  beq store_high
  asl
  asl
  dey
  bra shift_high
store_high:
  sta work
  lda fx_obj_count
  lsr
  lsr
  tax
  sep #$20
  lda fx_obj_next+128,x
  ora work
  sta fx_obj_next+128,x
  rep #$20
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
  ldx #134
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

; forced blank中に32枠のlow128bytes、対応するhigh8bytesだけ更新。
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
  lda fx_obj_present_count
  cmp last_upload_count
  bcs :+
  lda last_upload_count
:
  cmp #1
  bcs :+
  lda #1
:
  asl
  asl
  sta f:$004305
  clc
  adc #8
  sta fx_obj_dma_bytes
  lda fx_obj_present_count
  sta last_upload_count
  sep #$20
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

high_masks: .word 1,4,16,64
.segment "RODATA"
player_tiles: .incbin "assets/obj_tiles.bin"
bullet_tiles: .incbin "assets/obj_bullets.bin"
