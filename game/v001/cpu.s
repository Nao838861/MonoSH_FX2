.setcpu "65816"
.smart
.import _main, _fx_frame, _fx_buttons, _fx_packet_count, _fx_packet
.import fx_audio_init: far, fx_audio_process: far
.import _fx_ground_vptr, _fx_ground_c1ptr, _fx_ground_c3ptr
.import _fx_ground_far_y
.import _fx_far_d_acc, fx_sky_pointer
.import _fx_ground_hptr
.import ground_empty
.import fx_upload_ground
.import _fx_ground_far_xptr
.import _fx_sky_color, fx_latch_obj, fx_upload_obj, fx_prepare_obj_dma
.import fx_plan_dma, fx_commit_dma, fx_dma_count, fx_dma_desc, fx_dma_bytes
.import fx_read_gsu_spans
.import fx_latch_color, fx_upload_color, fx_color_dma_count, fx_color_dma_bytes
.import color_palette, color_boot_map, fx_stage_color, fx_color_staged, fx_upload_color_palette
.ifdef FX_GSU_COLOR
.import fx_read_gsu_color_plan
.endif
.import __COLORRODATA_LOAD__, __COLORRODATA_RUN__, __COLORRODATA_SIZE__
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
  ; $0400..$15ffはカラー、$1600..$17ffは音源用。native scratch($0160..$02xx)と
  ; C stack($1c00から下降、$1800より上)・HDMA状態($1d00台)から分離。
  ldx #0
  lda #0
clear_color_ram:
  sta f:$7e0400,x
  inx
  inx
  cpx #$1400
  bne clear_color_ram
  ldx #.loword(__COLORRODATA_LOAD__)
  ldy #__COLORRODATA_RUN__
  lda #(__COLORRODATA_SIZE__-1)
  mvn #$00,#$7e
  pea $0000
  plb
  plb
  jsl fx_audio_init
  sep #$20
  stz $2105
  lda #3
  sta $210b                 ; BG1森林 CHR=$6000、BG2 FX CHR=$0000。
  lda #$32
  sta $210c                 ; BG3 CHR=$4000, BG4 CHR=$6000 bytes
  lda #$40
  sta $2108                 ; BG2 map=$8000
  lda #$49
  sta $2107                 ; BG1森林 map=$9000、64x32。
  lda #$51
  sta $2109                 ; BG3 map=$a000
  lda #$59
  sta $210a                 ; BG4 map=$b000、OBJ CHR=$c000〜$ffff。
  lda #$1f
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
  ; 裏のBG2 map($8800)も同じtile番号で初期化する。
  rep #$20
  lda #$4400
  sta $2116
  lda #.loword(color_boot_map)
  sta $4302
  lda #2048
  sta $4305
  sep #$20
  stz $4304
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
  cpx #obj_palette_data_end-obj_palette_data
  bne obj_palette
  stz $2121
  ldx #0
near_palette:
  lda f:scenery_palette_data,x
  sta $2122
  inx
  cpx #64
  bne near_palette
  lda #96
  sta $2121
far_palette:
  lda f:scenery_palette_data,x
  sta $2122
  inx
  cpx #128
  bne far_palette
  lda #32
  sta $2121
  ldx #0
initial_fx_palette:
  lda f:color_palette,x
  sta $2122
  inx
  cpx #64
  bne initial_fx_palette
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
obj_palette_data_end:
scenery_palette_data: .incbin "assets/scenery_palette.bin"

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
  lda #$fe
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

_fx_present:
  php
  rep #$30
  jsr fx_latch_color
  jsr fx_plan_dma
  .ifndef FX_GSU_COLOR
  ; 前の画像転送後に残る黒帯で裏mapを準備できれば、追加fieldは不要。
  lda fx_color_dma_count
  beq color_early_ready
  sep #$20
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  pha
  lda f:$00213d
  and #1
  bne color_early_high
  pla
  cmp #15
  bcc color_early_stage
  cmp #203
  bcc color_early_ready
  bra color_early_stage
color_early_high:
  pla
color_early_stage:
  lda #$80
  sta f:$002100
  jsr fx_stage_color
color_early_ready:
  .endif
  rep #$30
  ; 小さい転送は203行目に間に合わなくても黒帯内で完了できる。
  ; dynamicDmaDeadlineでは転送量に応じ220/226/233行目まで許可。全FBは203行目。
  ; 設定費用をbyte換算し、翌22行のOBJ準備より前に転送を終える。
  .ifdef FX_DYNAMIC_DMA
  jsr select_dma_deadline
  .else
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
  .endif
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
  lda _fx_far_d_acc
  .repeat 7
    lsr
  .endrepeat
  and #$1ff
  sta f:$7e1d14
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
  ; S-CPU revision 1 can fail when DMA ends at an active HDMA boundary.
  ; Use the fast copy only in the middle of VBlank, with enough room even
  ; for the maximum 1280-byte legacy packet. Keep MVN everywhere else.
  sep #$20
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #225
  bcc packet_mvn
  cmp #251
  bcs packet_mvn
  rep #$20
  lda f:$7e1d02
  ; Reverse DMA reads WRAM through B-bus $2180 and writes cartridge SRAM
  ; on the A bus. GSU is stopped; this is not the invalid WRAM-to-WRAM DMA.
  sta f:$004305
  lda #$8080
  sta f:$004300
  lda #$0020
  sta f:$004302
  lda #_fx_packet
  sta f:$002181
  sep #$20
  lda #$70
  sta f:$004304
  lda #0
  sta f:$002183
  lda #1
  sta f:$00420b
  rep #$20
  bra copy_clear_spans
packet_mvn:
  rep #$30
  lda f:$7e1d02
  dec
  ldx #_fx_packet
  ldy #$0020
  mvn #$7e,#$70
  pea $7e7e
  plb
  plb
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
  jsl fx_audio_process
  .ifdef FX_GSU_COLOR
  jsr fx_read_gsu_color_plan
  .endif
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
  .ifdef FX_DYNAMIC_DMA
  jsr select_dma_deadline
  .else
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
  .endif
  sep #$20
  .endif
  ; A large partial FB can overflow the same blank as a full transfer once
  ; color spans are added. Use the FB planner's conservative weighted limit,
  ; rather than testing only the exact 12 KiB case. Stage color separately.
  rep #$30
  lda fx_dma_count
  .repeat 6
    asl
  .endrepeat
  clc
  adc fx_dma_bytes
  clc
  adc fx_color_dma_bytes
  pha
  lda fx_color_dma_count
  .repeat 6
    asl
  .endrepeat
  clc
  adc 1,s
  sta 1,s
  pla
  cmp #12000
  bcc color_stage_ready
  lda fx_color_dma_count
  beq color_stage_ready
  lda fx_color_staged
  bne color_stage_ready
  sep #$20
wait_color_blank:
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcc wait_color_blank
  lda f:$004212
  and #$40
  beq wait_color_blank
  lda #$80
  sta f:$002100
  jsr fx_stage_color
wait_color_next_field:
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcs wait_color_next_field
color_stage_ready:
  jsr fx_prepare_obj_dma
  .ifdef FX_DMA_DEADLINE_PROBE
  sep #$20
  .export dma_probe_delay
dma_probe_delay:
  ; 帯域検証専用ROM: 許可された最終行まで意図的に待って転送する。
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp f:$7e1d10
  bne dma_probe_delay
  .endif
  sep #$20
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
  ; Visible output ended on line 202. Force blank immediately after admission;
  ; waiting for this black scanline's HBlank would waste most of a scanline.
  lda #$80
  sta f:$002100
  lda #0
  sta f:$00420c             ; 黒帯内だけHDMAを止め、共有スクロールラッチを保護。
  jsr update_ground_pointers
  lda f:$7e1d0a
  sta f:$002114
  lda f:$7e1d0b
  sta f:$002114
  lda f:$7e1d0a
  sta f:$00210e
  lda f:$7e1d0b
  sta f:$00210e
  lda f:$7e1d14
  sta f:$00210d
  lda f:$7e1d15
  sta f:$00210d
  jsr fx_upload_obj
dma_started:
  lda #3
  sta f:$7e1df0
  jsr fx_upload_color_palette
  lda #$fe
  sta f:$00420c
  jsr fx_upload_color
  rep #$20
  lda #$1801
  sta f:$004300
  sep #$20
  lda #$70
  sta f:$004304
  rep #$30
  ldx #0
  ldy fx_dma_count
  beq dma_finished
dma_span:
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
  ; 区間数をYで数え、WRAMの読戻し・DEC・BRAを各区間から外す。
  dey
  bne dma_span
  stz fx_dma_count           ; 従来どおり完了時は0。次のclear表は別に保持する。
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

  .ifdef FX_DYNAMIC_DMA
select_dma_deadline:
  .export select_dma_deadline
  rep #$30
  ; W=bytes+64*区間数+768。区間設定を64bytes換算し、HDMA等の固定費も予約。
  ; 設定・OBJ転送に最大4行を予約し、完了を翌21行より前へ収める。
  ; A/Xは16bit。全FBなど大きい転送は従来の203行を守る。
  lda #203
  sta f:$7e1d10
  lda fx_dma_count
  .repeat 6
    asl
  .endrepeat
  clc
  adc fx_dma_bytes
  clc
  adc #(768+64)             ; 切替時CGRAM64byteも最大費用として予約。
  ldx fx_color_staged
  bne color_deadline_no_map
  clc
  adc fx_color_dma_bytes
  pha
  lda fx_color_dma_count
  .repeat 6
    asl
  .endrepeat
  clc
  adc 1,s
  sta 1,s
  pla
color_deadline_no_map:
  cmp #(FX_DMA_ADMISSION_BYTES+1)
  bcs deadline_done
  .ifdef FX_FINE_DMA
  ; Wを170byte/行で割り、受付を220..255行で細かく選ぶ。
  ; D=278-floor(W/170)。D+4+W*8/1364 <283（翌21行の前）。
  ; 768bytesの固定予約と64bytes/区間もWへ含めた保守的な上限。
  .export dma_deadline_fine, dma_last_line
dma_last_line = 255
dma_deadline_fine:
  sta f:$004204
  sep #$20
  lda #170
  sta f:$004206
  rep #$20
  lda #278
  sec
  .repeat 8
    nop                    ; dividerの16 CPU cyclesを確実に待つ。
  .endrepeat
  sbc f:$004214
  cmp #(dma_last_line+1)
  bcc fine_save
  lda #dma_last_line
fine_save:
  sta f:$7e1d10
  rts
  .else
  ldx #220
  cmp #8961
  bcs deadline_save
  ldx #226
  cmp #7681
  bcs deadline_save
  ldx #233
deadline_save:
  txa
  sta f:$7e1d10
  .endif
deadline_done:
  rts
  .endif

blank_table:
  ; 22行目は輝度0でOBJ評価/CHR fetchを再開し、23行目のOBJを用意する。
  ; 全FB+OAM DMAは21行目までに終える。表示範囲23..202は180行のまま。
  .byte 21,$80,1,$00,127,$0f,53,$0f,22,$80,1,$80,0


.segment "GFX"
  .incbin "assets/ppu.bin"
.segment "HEADER"
  .byte 0,0,"FX2G",0,0,0,0,0,0,0,$06,0,0
  .byte "MONOSH FX2 GAME V001 "
  .byte $20,$15,$0b,$00,$01,$33,$00
  .word $ffff,$0000
  .res $20,$00
