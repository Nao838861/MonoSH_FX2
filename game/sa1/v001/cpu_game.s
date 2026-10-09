.setcpu "65816"
.smart
.macpack longbranch
.import _main, _fx_frame, _fx_buttons, _fx_packet_count, _fx_packet
.import fx_audio_init: far, fx_audio_process: far
.import _fx_ground_vptr, _fx_ground_c1ptr, _fx_ground_c3ptr
.import _fx_ground_far_y
.import _fx_far_d_acc, _fx_far_u_acc, _monosh_ground_offset, fx_sky_pointer
.include "assets4/background4.inc"
.include "assets4/source4.inc"
.if FX4_COLOR
.import player4_upload_bytes
.endif
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
.import __SA1_LOAD__, __SA1_SIZE__
.import sa1_entry
.importzp c_sp
.export __STARTUP__ : absolute = 1
.export _fx_present, _fx_read_input, _fx_send_ground
.export reset, game_started, render_started, render_finished, dma_started, dma_finished
.export render_second_started, render_second_finished
.export audio4_first_done, audio4_second_done
.export half_dma_finished
.if FX4_COLOR
.export fx4_wait_obj_blank
.endif
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
  lda #4
  sta $2220
  inc
  sta $2221
  inc
  sta $2222
  inc
  sta $2223
  rep #$30
  ldx #0
  ldy #0
  lda #$ffff
  mvn #$c1,#$7f
  ldx #0
  ldy #$2000
  lda #$ffff
  mvn #$c2,#$7e
  pea $0000
  plb
  plb
  jsl fx_audio_init
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
  .if FX4_COLOR
  ora #$10
  .endif
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
  lda #$c3
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
  lda #$80
  sta $2226
  stz $2229
  rep #$30
  ldx #.loword(__SA1_LOAD__)
  ldy #$3200
  lda #__SA1_SIZE__-1
  mvn #$00,#$00
  ldx #$1e
clear_mailbox:
  stz $3100,x
  dex
  dex
  bpl clear_mailbox
  lda #sa1_entry
  sta $2203
  sep #$20
  stz $2200
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

; SA-1の線形4bpp出力をキャラクタ変換DMAでPPUへ送る最初の統合版。
; 全画面転送は二つの非表示期間に分割する。60fps達成版ではない。
_fx_present:
  php
  rep #$30
  stz fx4_build_skip
  stz fx4_dma_bytes
  jsr fx_latch_obj
  jsr fx_upload_ground
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
  lda _fx_far_d_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta f:$003108
  lda _fx_far_u_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta f:$00310a
  lda _monosh_ground_offset
  and #255
  sta f:$00310c
  lda _fx_packet_count
  sta f:$003106
  asl
  asl
  clc
  adc _fx_packet_count
  asl
  beq no_packet
  dec
  ldx #_fx_packet
  ldy #0
  mvn #$7e,#$43
  pea $7e7e
  plb
  plb
no_packet:
render_started:
  lda #1
  sta f:$003100
  sep #$30
  jsr _fx_frame
  sep #$20
wait_sa1:
  lda f:$003104
  beq wait_sa1
render_finished:
render_second_started:
render_second_finished:
  jsl fx_audio_process
audio4_first_done:
audio4_second_done:
  rep #$30
  lda f:$00311a
  sta fx4_desc_count
  asl
  clc
  adc fx4_desc_count
  asl
  sta fx4_desc_count
  beq no_descriptors
  dec
  ldx #$0800
  ldy #fx4_descriptors
  mvn #$43,#$7e
  pea $7e7e
  plb
  plb
no_descriptors:
  lda fx4_page
  eor #$3000
  sta fx4_page
  sta fx4_upload_vram
  stz fx4_desc_pos
  sep #$20
  lda #$15
  sta f:$002231
  rep #$20
  lda #0
  sta f:$002232
  sep #$20
  .ifdef SA1_PADDED
  lda #$41
  .else
  lda #$40
  .endif
  sta f:$002234
  rep #$20
  lda #$07c0
  sta f:$002235
transfer_chunk:
  sep #$20
  jsr wait_blank
  rep #$30
  stz fx4_half_bytes
  lda #$1801
  sta f:$004300
  sep #$20
  .ifdef SA1_PADDED
  lda #$41
  .else
  lda #$40
  .endif
  sta f:$004304
  rep #$30
transfer_descriptor:
  ldx fx4_desc_pos
  cpx fx4_desc_count
  bcs transfer_complete
  lda fx4_descriptors,x
  clc
  adc fx4_half_bytes
  cmp #10001
  bcs transfer_chunk
  sta fx4_half_bytes
  lda fx4_descriptors,x
  sta f:$004305
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  lda fx4_descriptors+2,x
  sta f:$004302
  lda fx4_descriptors+4,x
  clc
  adc fx4_upload_vram
  sta f:$002116
  sep #$20
dma_started:
  lda #1
  sta f:$00420b
half_dma_finished:
  rep #$30
  lda fx4_desc_pos
  clc
  adc #6
  sta fx4_desc_pos
  bra transfer_descriptor
transfer_complete:
  sep #$20
  jsr update_ground_pointers
  lda f:$7e1d0a
  sta f:$002112
  lda f:$7e1d0b
  sta f:$002112
  lda #$95
  sta f:$002231
  jsr fx_upload_obj
  lda fx4_page+1
  lsr
  lsr
  lsr
  lsr
  sta f:$00210b
  rep #$20
  inc fx4_generation
  lda #0
  sta f:$003100
wait_ack:
  lda f:$003104
  bne wait_ack
dma_finished:
  sep #$20
  lda #1
  sta f:$004200
  plp
  rts
wait_blank:
  .a8
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcc wait_blank
  cmp #205
  bcs wait_blank
wait_hblank:
  lda f:$004212
  and #$40
  beq wait_hblank
  lda #$80
  sta f:$002100
  rts
fx4_wait_obj_blank:
  php
  sep #$20
  jsr wait_blank
  plp
  rts
blank_table:
  .byte 21,$80,1,$00,127,$0f,53,$0f,22,$80,1,$80,0
.include "math4.inc"
.segment "GFX"
.incbin "ppu_sa1.bin"
.segment "HEADER"
.res $10,0
.byte "MONOSH SA1 4BPP GAME "
.byte $23,$34,$0d,$08,$01,$33,$00
.word $ffff,0
.res $20,0
