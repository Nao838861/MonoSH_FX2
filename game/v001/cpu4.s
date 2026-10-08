.setcpu "65816"
.smart
.macpack longbranch
.import _main, _fx_frame, _fx_buttons, _fx_packet_count, _fx_packet
.import _fx_ground_vptr, _fx_ground_c1ptr, _fx_ground_c3ptr
.import _fx_ground_far_y
.import _fx_far_d_acc, _fx_far_u_acc, _monosh_ground_offset, fx_sky_pointer
.include "assets4/background4.inc"
.import _fx_ground_hptr
.import ground_empty
.import fx_upload_ground
.import _fx_ground_far_xptr
.import _fx_sky_color, fx_latch_obj, fx_upload_obj
.import fx_plan_dma, fx_commit_dma, fx_dma_count, fx_dma_desc, fx_dma_bytes
.import fx_read_gsu_spans
.ifndef FX_DMA_ADMISSION_BYTES
FX_DMA_ADMISSION_BYTES = 9984
.endif
.importzp c_sp
.export __STARTUP__ : absolute = 1
.export _fx_present, _fx_read_input, _fx_send_ground
.export reset, game_started, render_started, render_finished, dma_started, dma_finished
.export render_second_started, render_second_finished
.export half_dma_finished
.segment "BSS"
clear_initialized: .res 2
.export fx4_page, fx4_generation
.export fx4_build_skip
fx4_build_skip: .res 2
fx4_upload_vram: .res 2
fx4_page: .res 2
fx4_generation: .res 2

.export fx4_dma_bytes
.export fx4_half_bytes, fx4_desc_count
fx4_dma_bytes: .res 2
fx4_half_bytes: .res 2
fx4_descriptors = $0400
fx4_desc_count: .res 2
fx4_desc_pos: .res 2
fx4_latest: .res 2
.segment "BOOT"
reset:
  sei
  clc
  xce
  rep #$30
  lda #$1fff
  tcs
  sep #$20
  lda #$80
  sta $2100
  stz $4200
  stz $420c
  stz $420b
  lda #$ff
  sta $4201
  rep #$30
  ldx #0
  ldy #0
  lda #$ffff
  mvn #$41,#$7f
  ldx #0
  ldy #$2000
  lda #$ffff
  mvn #$42,#$7e
  pea $0000
  plb
  plb
  sep #$20
  lda #1
  sta $2105
  stz $210b                 ; BG1=4bpp FX page0, BG2 disabled
  lda #6
  sta $210c                 ; BG3 CHR byte C000, tiles begin at index256
  lda #$60
  sta $2107                 ; BG1 map byte C000 (32x32)
  lda #$79
  sta $2109                 ; BG3 map byte F000 (64x32)
  lda #5
  sta $212c                 ; BG1 FX + BG3 ground. OBJ merged by GSU.
  stz $212d
  stz $2133
  stz $210d
  stz $210d
  lda #$f3
  sta $210e
  lda #$ff
  sta $210e
  stz $2111
  stz $2111
  lda #$f3
  sta $2112
  lda #$ff
  sta $2112
  lda #$80
  sta $2115
  rep #$20
  stz $2116
  lda #$1801
  sta $4300
  stz $4302
  stz $4305                 ; 起動時だけVRAM全64KBを転送
  sep #$20
  lda #$43
  sta $4304
  lda #1
  sta $420b
  ; 各BGの白黒palette。色0透明、1暗色、3白。
  stz $2121
  ldx #0
palette_loop:
  txa
  and #3
  cmp #3
  beq white
  stz $2122
  stz $2122
  bra next_color
white:
  lda #$ff
  sta $2122
  lda #$7f
  sta $2122
next_color:
  inx
  cpx #128
  bne palette_loop
  ; 空の紫。カラーOBJの絵柄・CGRAMは起動時だけ転送する。
  stz $2121
  lda f:$7e0000+_fx_sky_color
  sta $2122
  lda f:$7e0001+_fx_sky_color
  sta $2122
  lda #128
  sta $2121
  ldx #0
obj_palette:
  lda f:obj_palette_data,x
  sta $2122
  inx
  cpx #64
  bne obj_palette
  lda #16
  sta $2121
  ldx #0
fx_palette:
  lda f:fx_palette_data,x
  sta $2122
  inx
  cpx #32
  bne fx_palette
  lda #$63                  ; size選択3=small16、大32、CHR byte base C000。
  sta $2101
  stz $2102
  stz $2103
  ldx #0
hide_objects:
  stz $2104
  lda #240
  sta $2104
  stz $2104
  stz $2104
  inx
  cpx #128
  bne hide_objects
  ldx #0
clear_high_oam:
  stz $2104
  inx
  cpx #32
  bne clear_high_oam
  ; HDMA1は上下22行黒帯。224行のうち180行だけ表示。
  lda #$00
  sta $4310
  sta $4311
  lda #$21
  sta $4314
  rep #$20
  lda #.loword(blank_table)
  sta $4312
  sep #$20
  lda #$7f
  sta $4314
  ; CPUデータを7E、コードを7FとしてCへ。
  lda #1
  sta $3039
  sta $3033
  lda #$a0
  sta $3037
  lda #8
  sta $3038
  stz $303c
  lda #1
  sta $3034
  lda #$39
  sta $303a
  lda #2
  sta $420c                ; 初回field開始時からINIDISP HDMAを初期化する
  rep #$30
  lda #$1c00
  sta c_sp
  sep #$30
  lda #$7e
  pha
  plb
  jml $7f0000 + game_started

obj_palette_data: .incbin "assets/obj_palette.bin"
scenery_palette_data: .incbin "assets/scenery_palette.bin"
fx_palette_data: .incbin "assets4/palette4.bin"

.segment "CODE"
.a8
.i8
game_started:
  ; 全HDMAチャネルを空テーブルで初期化してから開始する。
  ; 途中の走査線で未初期化チャネルを有効にするとCGRAMを破壊する。
  php
  rep #$30
  lda #$1dff
  sta f:$7e1d06
  sta f:$7e1d08
  sta f:$7e1d0c
  sta f:$7e1d0e
  sta f:$7e1d16
  lda #ground_empty
  sta f:$7e1d04
  sep #$20
  lda #0
  sta f:$7e1dff
  jsr _fx_send_ground
wait_initial_vblank:
  lda f:$004212
  and #$80
  beq wait_initial_vblank   ; 新規HDMAは次field先頭で初期化させる。
  lda #$7e
  sta f:$00420c
  plp
  jsr _main
  bra game_started

_fx_read_input:
  php
  ; Auto joypadがshift途中のJOY1を読むと、Y+左上($4a00)が
  ; Startを含む$1280に見え、押していないポーズが発生する。
  ; 読み取り前後にbusyを確認し、開始境界をまたいだ結果も捨てる。
  sep #$20
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcc wait_auto_joy
  cmp #230
  bcs wait_auto_joy
wait_auto_vblank:
  lda f:$004212
  and #$80
  beq wait_auto_vblank
wait_auto_joy:
  lda f:$004212
  and #1
  bne wait_auto_joy
  rep #$20
  lda f:$004218
  sta _fx_buttons
  sep #$20
  lda f:$004212
  and #1
  bne wait_auto_joy
  plp
  rts

_fx_send_ground:
  php
  rep #$30
  lda f:$7e1d04
  sta f:$004322
  lda f:$7e1d06
  sta f:$004332
  lda f:$7e1d08
  sta f:$004342
  lda f:$7e1d0e
  sta f:$004352
  lda f:$7e1d0c
  sta f:$004372
  lda f:$7e1d16
  sta f:$004362
  sep #$20
  lda #$7e
  sta f:$004334
  sta f:$004344
  sta f:$004354
  sta f:$004374
  sta f:$004364
  sta f:$004367
  lda #$43
  sta f:$004360
  lda #$21
  sta f:$004361
  lda #$7f
  sta f:$004324
  lda #2
  sta f:$004320
  sta f:$004350
  sta f:$004370
  lda #3
  sta f:$004330
  sta f:$004340
  lda #$12
  sta f:$004321
  lda #$21
  sta f:$004331
  sta f:$004341
  lda #$11
  sta f:$004351
  lda #$13
  sta f:$004371
  plp
  rts

; 固定設定は起動時の一度だけ。表示中の表を保持し、黒帯で次の表へ切替。
update_ground_pointers:
  php
  rep #$30
  lda f:$7e1d04
  sta f:$004322
  lda f:$7e1d06
  sta f:$004332
  lda f:$7e1d08
  sta f:$004342
  lda f:$7e1d0e
  sta f:$004352
  lda f:$7e1d0c
  sta f:$004372
  lda f:$7e1d16
  sta f:$004362
  plp
  rts

; 1描画=2フィールド。論理更新は各フィールド1回ずつ、完成画像のみ切替。
_fx_present:
  php
  rep #$30
  lda clear_initialized
  bne frame_prepared
  inc clear_initialized
  lda #0
  sta f:$700700            ; バッテリーRAMの前回起動のdirty flagを継承しない。
  jsr prepare_frame
frame_prepared:
  lda fx4_page
  eor #$3000
  sta f:$701016
  stz fx4_dma_bytes
  lda _fx_ground_vptr
  sta f:$7e1d04
  lda _fx_ground_c1ptr
  sta f:$7e1d06
  lda _fx_ground_c3ptr
  sta f:$7e1d08
  lda _fx_ground_far_y
  sta f:$7e1d0a
  lda fx_sky_pointer
  sta f:$7e1d16
  lda _fx_ground_far_xptr
  sta f:$7e1d0c
  lda _fx_ground_hptr
  sta f:$7e1d0e
start_render:
  lda #0
  sta f:$701010
  lda #0
  sta f:$701012
  lda #$8000
render_started:
  sta f:$00301e
  lda #1
  sta fx4_build_skip
  sep #$30
  jsr _fx_frame
  sep #$20
wait_gsu:
  lda f:$003030
  and #$20
  bne wait_gsu
render_finished:
  rep #$30
  lda fx4_page
  eor #$3000
  sta fx4_page
  sta fx4_upload_vram
  sta f:$002116
  lda #$2000
  sta f:$004302
  jsr plan_half
  sep #$20
  jsr wait_blank
  rep #$30
  jsr send_half
  lda #64
  sta f:$701010
  lda #0
  sta f:$701012
  lda #$8000
render_second_started:
  sta f:$00301e
  stz fx4_build_skip
  sep #$30
  jsr _fx_frame
  sep #$20
wait_second_gsu:
  lda f:$003030
  and #$20
  bne wait_second_gsu
render_second_finished:
  jsr prepare_frame
  rep #$30
  lda #$3800
  sta f:$004302
  jsr plan_half
  sep #$20
  jsr wait_blank
  jsr update_ground_pointers
  lda f:$7e1d0a
  sta f:$002112
  lda f:$7e1d0b
  sta f:$002112
  rep #$30
  lda fx4_page
  clc
  adc #$0c00
  sta fx4_upload_vram
  sta f:$002116
  lda #$3800
  sta f:$004302
  jsr send_half
  sep #$20
  lda fx4_page+1
  lsr
  lsr
  lsr
  lsr
  sta f:$00210b            ; 0 or3: complete 24KiB image becomes visible together.
  rep #$20
  inc fx4_generation
dma_finished:
  sep #$20
  lda #1
  sta f:$004200
  plp
  rts

; HDMAの既存黒帯203..261,0..22だけを利用する。
prepare_frame:
  php
  rep #$30
  jsr fx_upload_ground
  lda _fx_far_d_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta f:$701000
  lda _fx_far_u_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta f:$701008
  lda _monosh_ground_offset
  and #255
  clc
  adc #FX_BG_0_TOP
  sta f:$701002
  lda _monosh_ground_offset
  and #255
  clc
  adc #FX_BG_1_TOP
  sta f:$70100a
  lda #FX_BG_0_HEIGHT
  sta f:$701004
  lda #FX_BG_1_HEIGHT
  sta f:$70100c
  lda #FX_BG_0_ADDRESS
  sta f:$701006
  lda #FX_BG_1_ADDRESS
  sta f:$70100e
  lda _fx_packet_count
  sta f:$700000
  sta f:$7e1d00
  asl
  asl
  clc
  adc f:$7e1d00
  asl
  sta f:$7e1d02
  beq prepare_done
  dec
  ldx #_fx_packet
  ldy #$20
  mvn #$7e,#$70
  pea $7e7e
  plb
  plb
prepare_done:
  plp
  rts

wait_blank:
  .a8
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcc wait_blank
  cmp fx4_latest
  bcs wait_blank
wait_hblank:
  lda f:$004212
  and #$40
  beq wait_hblank
  lda #$80
  sta f:$002100
  rts

plan_half:
  .a16
  .i16
  lda f:$701160
  sta fx4_desc_count
  asl
  clc
  adc fx4_desc_count
  asl
  sta fx4_desc_pos
  lda f:$701162
  sta fx4_half_bytes
  lda fx4_desc_pos
  beq :+
  dec
  ldx #$1100
  ldy #fx4_descriptors
  mvn #$70,#$7e
  pea $7e7e
  plb
  plb
:
  ; Divide the exact byte budget by 164 bytes/scanline. Reserve CPU setup.
  lda fx4_half_bytes
  clc
  adc #163
  sta f:$004204
  sep #$20
  lda #164
  sta f:$004206
  rep #$20
  lda fx4_desc_count
  clc
  adc #1
  lsr
  sta fx4_latest
  lda #280
  sec
  sbc fx4_latest
  sec
  sbc f:$004214
  cmp #246
  bcc :+
  lda #245
:
  sta fx4_latest
  cmp #204
  bcs plan_budget_ready4
  ; 区間が多い最悪形状は、担当する二本の全帯へまとめる。最低でもline203に開始できる。
  lda #2
  sta fx4_desc_count
  lda #12
  sta fx4_desc_pos
  lda #12288
  sta fx4_half_bytes
  lda #204
  sta fx4_latest
  lda #6144
  sta fx4_descriptors
  sta fx4_descriptors+6
  lda f:$701010
  and #64
  beq plan_full_left4
  lda #$1800
plan_full_left4:
  clc
  adc #$2000
  sta fx4_descriptors+2
  clc
  adc #$3000
  sta fx4_descriptors+8
  lda fx4_descriptors+2
  sec
  sbc #$2000
  lsr
  clc
  adc fx4_page
  sta fx4_descriptors+4
  clc
  adc #$1800
  sta fx4_descriptors+10
plan_budget_ready4:
  rts
send_half:
  .a16
  .i16
  lda fx4_dma_bytes
  clc
  adc fx4_half_bytes
  sta fx4_dma_bytes
  lda #$1801
  sta f:$004300
  sep #$20
  lda #$70
  sta f:$004304
dma_started:
  rep #$30
  ldx #0
send_descriptor:
  cpx fx4_desc_pos
  bcs descriptors_done
  lda fx4_descriptors,x
  sta f:$004305
  lda fx4_descriptors+2,x
  sta f:$004302
  lda fx4_descriptors+4,x
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  rep #$30
  txa
  clc
  adc #6
  tax
  bra send_descriptor
descriptors_done:
half_dma_finished:
  rts

blank_table:
  .byte 21,$80,1,$00,127,$0f,53,$0f,22,$80,1,$80,0

 .include "math4.inc"
.segment "GFX"
  .incbin "assets4/ppu.bin"
.segment "HEADER"
  .byte 0,0,"FX2G",0,0,0,0,0,0,0,$06,0,0
  .byte "MONOSH FX2 4BPP 30FPS"
  .byte $20,$15,$0b,$00,$01,$33,$00
  .word $ffff,$0000
  .res $20,$00

