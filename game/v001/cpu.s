.setcpu "65816"
.smart
.import _main, _fx_frame, _fx_buttons, _fx_packet_count, _fx_packet
.import _fx_ground_vptr, _fx_ground_c1ptr, _fx_ground_c3ptr
.import _fx_ground_far_y
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
.segment "BSS"
clear_initialized: .res 2

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
  stz $2105
  stz $210b
  lda #$32
  sta $210c                 ; BG3 CHR=$4000, BG4 CHR=$6000 bytes
  lda #$40
  sta $2108                 ; BG2 map=$8000
  lda #$51
  sta $2109                 ; BG3 map=$a000
  lda #$58
  sta $210a                 ; BG4 map=$b000、OBJ CHR=$c000〜$ffff。
  lda #$1e
  sta $212c
  stz $212d
  stz $2133
  stz $210f
  stz $210f
  lda #$f3
  sta $2110
  lda #$ff
  sta $2110                 ; BG2だけ固定Y=-13。地面の投影には巻き込まない。
  stz $2111
  stz $2111
  stz $2113
  stz $2113
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
  cpx #32
  bne obj_palette
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
  lda #$80
  sta $3037
  lda #8
  sta $3038
  stz $303c
  lda #1
  sta $3034
  lda #$38
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
  lda #$be
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
  sep #$20
  lda #$7e
  sta f:$004334
  sta f:$004344
  sta f:$004354
  sta f:$004374
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
  plp
  rts

_fx_present:
  php
  rep #$30
  jsr fx_plan_dma
  ; 小さい転送は203行目に間に合わなくても黒帯内で完了できる。
  ; bytes+区間数*128が9.75KiB以下だけ220行目まで許可。全FBは203行目。
  ; 設定費用をbyte換算し、翌22行のOBJ準備より前に転送を終える。
  lda #203
  sta f:$7e1d10
  lda fx_dma_count
  .repeat 7
    asl
  .endrepeat
  clc
  adc fx_dma_bytes
  cmp #(FX_DMA_ADMISSION_BYTES+1)
  bcs :+
  lda #220
  sta f:$7e1d10
:
  jsr fx_upload_ground
  lda _fx_ground_vptr
  sta f:$7e1d04
  lda _fx_ground_c1ptr
  sta f:$7e1d06
  lda _fx_ground_c3ptr
  sta f:$7e1d08
  lda _fx_ground_far_y
  sta f:$7e1d0a
  lda _fx_ground_far_xptr
  sta f:$7e1d0c
  lda _fx_ground_hptr
  sta f:$7e1d0e
  ; PacketをGSUの停止中にだけ書く。
  lda _fx_packet_count
  sta f:$700000
  sta f:$7e1d00
  asl
  asl
  clc
  adc f:$7e1d00
  asl
  .ifndef FX_GSU_CLIP
    asl                    ; 通常commandは20byte、GSU clipは10byteのdraw。
  .endif
  sta f:$7e1d02
  beq copy_clear_spans
  dec
  ldx #_fx_packet
  ldy #$0020
  mvn #$7e,#$70             ; GSU STOP中にWRAM→cart RAMを連続コピー。
  pea $7e7e
  plb
  plb                      ; MVNが変更したDBRをCのWRAMへ戻す。
copy_clear_spans:
  .ifdef FX_GSU_CLIP
  lda clear_initialized
  bne start_render
  inc clear_initialized
  lda #0
  sta f:$700700
  bra start_render
  .else
  lda clear_initialized
  bne partial_clear
  inc clear_initialized
  lda #1
  sta f:$700008
  lda #0
  sta f:$700600
  lda #$3000
  sta f:$700602
  bra start_render
partial_clear:
  lda fx_dma_count
  sta f:$700008
  asl
  asl
  sta f:$7e1d12
  ldx #0
copy_clear:
  txa
  cmp f:$7e1d12
  bcs start_render
  lda fx_dma_desc,x
  sta f:$700600,x
  inx
  inx
  bra copy_clear
  .endif
start_render:
  jsr fx_latch_obj
  lda #.loword(render_entry_address)
  ; entryはGSU segment先頭$8000。
  lda #$8000
render_started:
  sep #$20
  lda #1
  sta f:$7e1df0
  rep #$20
  lda #$8000
  sta f:$00301e
  sep #$30
  jsr _fx_frame
  sep #$20
wait_gsu:
  lda f:$003030
  and #$20
  bne wait_gsu
render_finished:
  lda #2
  sta f:$7e1df0
  .if .defined(FX_GSU_CLIP) .and .not .defined(FX_FULL_TRANSFER)
  rep #$30
  lda f:$700008
  sta fx_dma_count
  .ifdef FX_DESCRIPTOR_DMA
  jsr fx_read_gsu_spans
  .else
  asl
  asl
  sta f:$7e1d12
  ldx #0
copy_gsu_dma:
  txa
  cmp f:$7e1d12
  bcs gsu_dma_copied
  lda f:$700600,x
  sta fx_dma_desc,x
  inx
  inx
  bra copy_gsu_dma
gsu_dma_copied:
  .endif
  lda f:$70000a
  sta fx_dma_bytes
  lda #203
  sta f:$7e1d10
  lda fx_dma_count
  .repeat 7
    asl
  .endrepeat
  clc
  adc fx_dma_bytes
  cmp #(FX_DMA_ADMISSION_BYTES+1)
  bcs :+
  lda #220
  sta f:$7e1d10
:
  sep #$20
  .endif
wait_bottom:
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcc wait_bottom
  cmp f:$7e1d10
  bcc wait_hblank
  beq wait_hblank
  bra wait_bottom
wait_hblank:
  lda f:$004212
  and #$40
  beq wait_hblank
  lda #$80
  sta f:$002100
  jsr update_ground_pointers
  lda f:$7e1d0a
  sta f:$002114
  lda f:$7e1d0b
  sta f:$002114
  lda #$be
  sta f:$00420c
  jsr fx_upload_obj
  rep #$20
  lda #$1801
  sta f:$004300
  sep #$20
  lda #$70
  sta f:$004304
dma_started:
  lda #3
  sta f:$7e1df0
  rep #$30
  ldx #0
dma_span:
  lda fx_dma_count
  beq dma_finished
  lda fx_dma_desc,x
  sta f:$002116
  asl
  clc
  adc #$2000
  sta f:$004302
  lda fx_dma_desc+2,x
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  inx
  inx
  inx
  inx
  dec fx_dma_count
  bra dma_span
dma_finished:
  jsr fx_commit_dma
  sep #$20
  lda #4
  sta f:$7e1df0
  lda #1
  sta f:$004200             ; auto joy、NMI/IRQは無効
  plp
  rts
render_entry_address = $8000

blank_table:
  ; 22行目は輝度0でOBJ評価/CHR fetchを再開し、23行目のOBJを用意する。
  ; 全FB+OAM DMAは20行目までに終える。表示範囲23..202は180行のまま。
  .byte 21,$80,1,$00,127,$0f,53,$0f,22,$80,1,$80,0


.segment "GFX"
  .incbin "assets/ppu.bin"
.segment "HEADER"
  .byte 0,0,"FX2G",0,0,0,0,0,0,0,$06,0,0
  .byte "MONOSH FX2 GAME V001 "
  .byte $20,$15,$0b,$00,$01,$33,$00
  .word $ffff,$0000
  .res $20,$00
