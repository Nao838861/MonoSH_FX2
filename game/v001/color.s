.setcpu "65816"
.smart
.macpack longbranch
.export fx_build_color, fx_color_build_done, fx_latch_color, fx_upload_color, fx_color_upload_done
.export _fx_toggle_color, fx_color_mode, fx_color_present_mode, fx_color_present_ptr
.export fx_color_next_ptr, fx_color_map0, fx_color_map1, fx_color_cells
.export fx_color_dma_count, fx_color_dma, fx_color_dma_bytes
.export color_palette
.export fx_stage_color, fx_color_staged, fx_color_vram_base, color_boot_map, fx_color_stage_done
.export color_clear_ready, color_next_draw, color_visible, color_prepare_cols, color_cols_done
.export color_rows, color_kernel_restore, color_skip_draw, color_clear_dirty
.export color_clear_dirty_row, color_clear_dirty_skip
.import _fx_draw, _fx_asset_width, _fx_asset_height
.import _monosh_runtime_frame_counter, order
.importzp packet_work
.segment "ZEROPAGE"
color_order: .res 2
color_draw: .res 2
color_left: .res 2
color_top: .res 2
color_right: .res 2
color_bottom: .res 2
color_w: .res 2
color_h: .res 2
color_aw: .res 2
color_ah: .res 2
color_du: .res 2
color_dv: .res 2
color_asset: .res 2
color_flags: .res 2
color_x0: .res 2
color_x1: .res 2
color_y0: .res 2
color_y1: .res 2
color_u: .res 2
color_v: .res 2
color_maxu: .res 2
color_maxv: .res 2
color_stepu: .res 2
color_stepv: .res 2
color_firststepu: .res 2
color_firststepv: .res 2
color_dst: .res 2
color_col: .res 2
color_row: .res 2
color_srcrow: .res 2
color_bits: .res 2
color_mul_arg: .res 2
color_mul_step: .res 2
color_mul_lo: .res 2
color_desc_index: .res 2
color_patch_offset: .res 2
color_kernel_start: .res 2
color_kernel_end: .res 2
color_mp: .res 2
color_cp: .res 2
color_bp: .res 2
.segment "DATA"
fx_color_mode: .byte 1
fx_color_next_ptr: .word fx_color_map0
fx_color_present_ptr: .word fx_color_map1
color_uploaded_mode: .byte 1
fx_color_vram_base: .word $4000
.segment "COLORBSS"
fx_color_map0: .res 768
fx_color_map1: .res 768
fx_color_present_mode: .res 1
color_next_mode: .res 1
color_initialized: .res 2
color_bounds0: .res 96
color_bounds1: .res 96
fx_color_dma: .res 48
fx_color_dma_count: .res 2
fx_color_dma_bytes: .res 2
fx_color_staged: .res 2
color_pending_vram: .res 2
.segment "COLORRODATA"
; Expanded final attribute bytes, deduplicated by complete 16-cell source row.
; Empty dictionary row zero lets the renderer omit an entirely transparent row.
fx_color_cells: .incbin "assets/bg_color/runtime_generated_rows.bin"
color_source_rows: .incbin "assets/bg_color/runtime_generated_sources.bin"
color_cell_offsets: .incbin "assets/bg_color/runtime_generated_offsets.bin"
.segment "BOOT"
color_palette: .incbin "assets/bg_color/palette.bin"
color_mono:
.repeat 8
  ; 0番は透明のまま。輪郭1番は純黒、陰影2番と明部3番は純白。
  .word 0, $0000, $7fff, $7fff
.endrepeat
color_boot_map:
.repeat 32,Row
  .repeat 32,Col
    .if Row<24
      .word (Col*24+Row)|$2000
    .else
      .word $2000
    .endif
  .endrepeat
.endrepeat
.segment "CODE"
.a16
.i16
_fx_toggle_color:
  php
  sep #$20
  lda fx_color_mode
  eor #1
  sta fx_color_mode
  plp
  rts

; 引数のbyteとQ8.8 stepを乗算。実際のsource範囲は128pixel以下なので16bit。
color_multiply:
  sep #$20
  lda color_mul_arg
  sta f:$004202
  lda color_mul_step
  sta f:$004203
  nop
  nop
  nop
  nop
  rep #$20
  lda f:$004216
  sta color_mul_lo
  sep #$20
  lda color_mul_arg
  sta f:$004202
  lda color_mul_step+1
  sta f:$004203
  nop
  nop
  nop
  nop
  rep #$20
  lda f:$004216
  xba
  and #$ff00
  clc
  adc color_mul_lo
  rts

fx_build_color:
  php
  rep #$30
  .ifdef FX_GSU_COLOR
  ; Geometry and palette sampling are computed beside the GSU framebuffer.
  ; CPU still owns mode latching and every PPU upload for this generation.
  sep #$20
  lda fx_color_mode
  sta color_next_mode
  jmp fx_color_build_done
  .endif
.a16
.i16
  ; 基準mapをnextへ。presentはGSUの描画と対応し、CPU先行中には変更しない。
  lda fx_color_next_ptr
  sta color_mp
  lda #color_bounds0
  ldx fx_color_next_ptr
  cpx #fx_color_map0
  beq :+
  lda #color_bounds1
:
  sta color_bp
  lda color_initialized
  bne color_clear_previous
  inc color_initialized
  lda fx_color_present_ptr
  sta color_mp
  jsr color_clear_map
  lda fx_color_next_ptr
  sta color_mp
  jsr color_clear_map
  bra color_clear_ready
color_clear_previous:
  jsr color_clear_dirty
color_clear_ready:
  ldy #0
color_reset_bounds:
  lda #32
  sta (color_bp),y
  iny
  iny
  lda #0
  sta (color_bp),y
  iny
  iny
  cpy #96
  bne color_reset_bounds
  sep #$20
  lda fx_color_mode
  sta color_next_mode
  rep #$20
  stz color_order
color_next_draw:
  lda color_order
  cmp packet_work+8
  jcs fx_color_build_done
  tay
  lda order,y
  tax
  sta color_draw
  lda _fx_draw+7,x
  and #$ff
  sta color_flags
  bit #$80
  beq :+
  lda _monosh_runtime_frame_counter
  bit #1
  jne color_skip_draw
:
  lda _fx_draw+6,x
  and #$ff
  sta color_asset
  tay
  lda _fx_asset_width,y
  and #$ff
  sta color_aw
  lda _fx_asset_height,y
  and #$ff
  sta color_ah
  tya
  asl
  tay
  lda color_cell_offsets,y
  clc
  adc #color_source_rows
  sta color_cp
  lda _fx_draw+4,x
  and #$ff
  jeq color_skip_draw
  sta color_w
  lsr
  sta color_left
  lda _fx_draw,x
  sec
  sbc color_left
  sta color_left
  clc
  adc color_w
  sta color_right
  jmi color_skip_draw
  jeq color_skip_draw
  lda color_left
  cmp #256
  bpl color_skip_draw_jump
  lda _fx_draw+5,x
  and #$ff
  jeq color_skip_draw
  sta color_h
  lda _fx_draw+2,x
  sec
  sbc #20
  sta color_bottom
  jmi color_skip_draw
  jeq color_skip_draw
  sec
  sbc color_h
  sta color_top
  cmp #192
  bpl color_skip_draw_jump
  bra color_visible
color_skip_draw_jump:
  jmp color_skip_draw
color_visible:
  lda color_left
  bpl :+
  lda #0
:
  lsr
  lsr
  lsr
  sta color_x0
  lda color_right
  cmp #257
  bcc :+
  lda #256
:
  dec
  lsr
  lsr
  lsr
  sta color_x1
  lda color_top
  bpl :+
  lda #0
:
  lsr
  lsr
  lsr
  sta color_y0
  lda color_bottom
  cmp #193
  bcc :+
  lda #192
:
  dec
  lsr
  lsr
  lsr
  sta color_y1
  ; GSUと同じfloor(source*256/destination)。CPUの16/8 dividerを使う。
  lda color_aw
  xba
  sta f:$004204
  sep #$20
  lda color_w
  sta f:$004206
  rep #$20
  .repeat 8
    nop
  .endrepeat
  lda f:$004216
  sta color_maxu
  lda f:$004214
  sta color_du
  asl
  asl
  asl
  sta color_stepu
  lda color_ah
  xba
  sta f:$004204
  sep #$20
  lda color_h
  sta f:$004206
  rep #$20
  .repeat 8
    nop
  .endrepeat
  lda f:$004216
  sta color_maxv
  lda f:$004214
  sta color_dv
  asl
  asl
  asl
  sta color_stepv
  lda color_aw
  xba
  sec
  sbc color_maxu
  sec
  sbc color_du
  sta color_maxu
  lda color_du
  sta color_mul_step
  lda color_x0
  asl
  asl
  asl
  clc
  adc #4
  sec
  sbc color_left
  bpl color_first_u_inside
  ; First tile center lies before the sprite. The next is only d+8 pixels away.
  clc
  adc #8
  cmp color_w
  bcc :+
  lda color_w
  dec
:
  sta color_mul_arg
  jsr color_multiply
  sta color_firststepu
  stz color_u
  bra color_first_u_ready
color_first_u_inside:
  cmp color_w
  bcc :+
  lda color_w
  dec
:
  sta color_mul_arg
  jsr color_multiply
  sta color_u
  lda color_stepu
  sta color_firststepu
color_first_u_ready:
  lda color_x0
  sta color_col
  asl
  asl
  asl
  clc
  adc color_col
  sta color_patch_offset
  clc
  adc #color_kernel
  sta color_kernel_start
color_prepare_cols:
  lda color_u
  cmp color_maxu
  bcc :+
  lda color_maxu
:
  sta color_bits
  lda color_flags
  bit #$10
  beq :+
  lda color_aw
  xba
  dec
  sec
  sbc color_bits
  sta color_bits
:
  lda color_bits
  xba
  and #$ff
  lsr
  lsr
  lsr
  clc
  adc #fx_color_cells
  ldx color_patch_offset
  sta f:$7f0000+color_kernel+1,x
  lda color_patch_offset
  clc
  adc #9
  sta color_patch_offset
  inc color_col
  lda color_col
  cmp color_x1
  beq color_prepare_next
  bcs color_cols_done
color_prepare_next:
  lda color_u
  clc
  adc color_firststepu
  sta color_u
  lda color_stepu
  sta color_firststepu
  jmp color_prepare_cols
color_cols_done:
  lda color_patch_offset
  clc
  adc #color_kernel
  sta color_kernel_end
  ldx color_patch_offset
  sep #$20
  lda #$60                 ; 最終列の次の命令を一時RTSにする。
  sta f:$7f0000+color_kernel,x
  rep #$20
  lda color_ah
  xba
  sec
  sbc color_maxv
  sec
  sbc color_dv
  sta color_maxv
  lda color_dv
  sta color_mul_step
  lda color_y0
  asl
  asl
  asl
  clc
  adc #4
  sec
  sbc color_top
  bpl color_first_v_inside
  ; First tile center lies before the sprite. The next is only d+8 pixels away.
  clc
  adc #8
  cmp color_h
  bcc :+
  lda color_h
  dec
:
  sta color_mul_arg
  jsr color_multiply
  sta color_firststepv
  stz color_v
  bra color_first_v_ready
color_first_v_inside:
  cmp color_h
  bcc :+
  lda color_h
  dec
:
  sta color_mul_arg
  jsr color_multiply
  sta color_v
  lda color_stepv
  sta color_firststepv
color_first_v_ready:
  lda color_y0
  sta color_row
color_rows:
  lda color_v
  cmp color_maxv
  bcc :+
  lda color_maxv
:
  sta color_bits
  lda color_flags
  bit #$20
  beq :+
  lda color_ah
  xba
  dec
  sec
  sbc color_bits
  sta color_bits
:
  lda color_bits
  xba
  and #$f8
  lsr
  lsr                     ; source cell row * 2, an index into the row pointers
  tay
  lda (color_cp),y
  beq color_row_done       ; all 16 cells transparent, keep previous attributes
  sta color_srcrow
  lda color_row
  asl
  asl
  tay
  lda (color_bp),y
  cmp color_x0
  bcc :+
  lda color_x0
  sta (color_bp),y
:
  iny
  iny
  lda color_x1
  inc
  cmp (color_bp),y
  bcc :+
  sta (color_bp),y
:
  sep #$20
  lda color_row
  cmp #16
  lda #0
  bcc :+
  inc
:
  sta f:$7f0000+color_kernel+10*9+6
  lda color_row
  cmp #8
  lda #1
  bcc :+
  inc
:
  sta f:$7f0000+color_kernel+21*9+6
  rep #$20
  ldy color_srcrow
  phd
  lda color_row
  .repeat 5
    asl
  .endrepeat
  clc
  adc color_mp
  tcd                      ; 出力先の行をdirect pageにする。
  sep #$20                ; keep 16-bit Y for the dictionary row offset
  jsr color_dispatch
  rep #$30
  pld
color_row_done:
  lda color_row
  inc
  sta color_row
  cmp color_y1
  beq color_next_row
  bcs color_kernel_restore
color_next_row:
  lda color_v
  clc
  adc color_firststepv
  sta color_v
  lda color_stepv
  sta color_firststepv
  jmp color_rows
color_kernel_restore:
  lda color_kernel_end
  sec
  sbc #color_kernel
  tax
  sep #$20
  lda #$b9
  cpx #32*9
  bcc :+
  lda #$60
:
  sta f:$7f0000+color_kernel,x
  rep #$20
color_skip_draw:
  inc color_order
  inc color_order
  jmp color_next_draw
fx_color_build_done:
  plp
  rts

; Each column is 9 bytes. Patch only its source-column address per draw.
.a8
.i16
color_dispatch:
  jmp (color_kernel_start)
color_kernel:
.repeat 32,Col
  .scope .ident(.sprintf("ColorColumn%d",Col))
    lda fx_color_cells,y
    beq empty
    ora #((Col*24)>>8)
    sta Col
empty:
  .endscope
.endrepeat
  rts
.a16
.i16

color_clear_dirty:
  rep #$30
  stz color_row
color_clear_dirty_row:
  lda color_row
  asl
  asl
  tay
  lda (color_bp),y
  asl
  asl
  clc
  adc #color_clear_kernel
  sta color_kernel_start
  iny
  iny
  lda (color_bp),y
  beq color_clear_dirty_skip
  asl
  asl
  tax
  stx color_patch_offset
  sep #$20
  lda #$60
  sta f:$7f0000+color_clear_kernel,x
  lda color_row
  cmp #16
  lda #$20
  bcc :+
  inc
:
  sta f:$7f0000+color_clear_kernel+10*4+1
  lda color_row
  cmp #8
  lda #$21
  bcc :+
  inc
:
  sta f:$7f0000+color_clear_kernel+21*4+1
  rep #$20
  phd
  lda color_row
  .repeat 5
    asl
  .endrepeat
  clc
  adc color_mp
  tcd
  sep #$30
  jsr color_dispatch
  rep #$30
  pld
  ldx color_patch_offset
  sep #$20
  lda #$a9
  cpx #32*4
  bcc :+
  lda #$60
:
  sta f:$7f0000+color_clear_kernel,x
  rep #$20
color_clear_dirty_skip:
  inc color_row
  lda color_row
  cmp #24
  jne color_clear_dirty_row
  rts
.a8
.i8
color_clear_kernel:
.repeat 32,Col
  lda #($20|((Col*24)>>8))
  sta Col
.endrepeat
  rts
.a16
.i16

; 3種類の行パターンを各8行。tile番号上位とpriorityを毎画像復元。
color_clear_map:
  ldy #0
  .repeat 3,Group
    .scope .ident(.sprintf("ColorClear%d",Group))
    ldx #8
clear_rows:
    .repeat 16,Pair
      lda #(($20|(((Pair*2)*24+Group*8)>>8))|(($20|(((Pair*2+1)*24+Group*8)>>8))<<8))
      sta (color_mp),y
      iny
      iny
    .endrepeat
    dex
    bne clear_rows
    .endscope
  .endrepeat
  rts

fx_latch_color:
  php
  rep #$30
  .ifdef FX_GSU_COLOR
  lda color_initialized
  bne :+
  inc color_initialized
  lda #0
  sta f:$701604            ; Reset shadow-map validity before the first GSU pass.
:
  .endif
  lda #1
  sta fx_color_dma_count
  lda #768
  sta fx_color_dma_bytes
  sta fx_color_dma+2
  lda #$4000
  sta fx_color_dma
  lda #4
  sta color_desc_index
  lda fx_color_next_ptr
  ldx fx_color_present_ptr
  sta fx_color_present_ptr
  stx fx_color_next_ptr
  sep #$20
  lda color_next_mode
  sta fx_color_present_mode
  plp
  rts

; forced blank中だけ呼ぶ。BG2 mapのhigh byteだけ、tile番号とpriorityを保持。
fx_upload_color:
  php
  rep #$30
  lda fx_color_staged
  beq :+
  stz fx_color_staged
  lda color_pending_vram
  sta fx_color_vram_base
  xba
  sep #$20
  sta f:$002108
  jmp color_upload_spans_done
:
  lda fx_color_dma_count
  bne :+
  sep #$20
  lda fx_color_present_mode
  cmp color_uploaded_mode
  jeq fx_color_upload_done
  rep #$20
:
  lda #$1900
  sta f:$004300
  sep #$20
  lda #$80
  sta f:$002115
  .ifdef FX_GSU_COLOR
  lda #$70
  .else
  lda #$7e
  .endif
  sta f:$004304
  rep #$30
  ldx #0
color_upload_spans:
  cpx color_desc_index
  bcs color_upload_spans_done
  lda fx_color_dma,x
  sec
  sbc #$4000
  clc
  adc fx_color_vram_base
  sta f:$002116
  lda fx_color_dma,x
  sec
  sbc #$4000
  clc
  .ifdef FX_GSU_COLOR
  adc #$1000
  .else
  adc fx_color_present_ptr
  .endif
  sta f:$004302
  lda fx_color_dma+2,x
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  inx
  inx
  inx
  inx
  bra color_upload_spans
color_upload_spans_done:
fx_color_upload_done:
  plp
  rts

.export fx_upload_color_palette
fx_upload_color_palette:
  php
  rep #$30
  sep #$20
  lda fx_color_present_mode
  cmp color_uploaded_mode
  beq fx_color_palette_done
  sta color_uploaded_mode
  rep #$20
  lda #.loword(color_palette)
  ldx fx_color_present_mode
  txa
  and #$ff
  bne color_upload_palette
  lda #.loword(color_mono)
  bra color_upload_cgram
color_upload_palette:
  lda #.loword(color_palette)
color_upload_cgram:
  sta f:$004302
  lda #$2200
  sta f:$004300
  lda #64
  sta f:$004305
  sep #$20
  lda #0
  sta f:$004304
  lda #32
  sta f:$002121
  lda #1
  sta f:$00420b
fx_color_palette_done:
  plp
  rts

; 大きいFB転送は別fieldの黒帯で裏mapを準備する。表mapは一切変えない。
fx_stage_color:
  php
  rep #$30
  inc fx_color_staged
  lda fx_color_vram_base
  eor #$0400
  sta color_pending_vram
  sta f:$002116
  lda #$1900
  sta f:$004300
  .ifdef FX_GSU_COLOR
  lda #$1000
  .else
  lda fx_color_present_ptr
  .endif
  sta f:$004302
  lda #768
  sta f:$004305
  sep #$20
  .ifdef FX_GSU_COLOR
  lda #$70
  .else
  lda #$7e
  .endif
  sta f:$004304
  lda #$80
  sta f:$002115
  lda #1
  sta f:$00420b
fx_color_stage_done:
  plp
  rts

.ifdef FX_GSU_COLOR
.export fx_read_gsu_color_plan
; Read only the compact span descriptors while GSU is stopped. Attribute data
; stays in cartridge SRAM and DMA goes directly to VRAM under CPU ownership.
fx_read_gsu_color_plan:
  php
  rep #$30
  lda f:$701600
  sta fx_color_dma_count
  asl
  asl
  sta color_desc_index
  sta f:$004305
  lda f:$701602
  sta fx_color_dma_bytes
  lda color_desc_index
  beq color_plan_done
  lda #$8000
  sta f:$004300
  lda #$1620
  sta f:$004302
  lda #fx_color_dma
  sta f:$002181
  sep #$20
  lda #$70
  sta f:$004304
  lda #0
  sta f:$002183
  lda #1
  sta f:$00420b
color_plan_done:
  plp
  rts
.endif
