.setcpu "65816"
.smart
.macpack longbranch
.export fx_plan_dma, fx_commit_dma, fx_dma_count, fx_dma_desc, fx_dma_bytes
.export fx_reset_next_bounds, fx_add_next_bounds
.import _fx_packet, _fx_packet_count
.segment "ZEROPAGE"
packet_ptr: .res 2
.segment "BSS"
current_min: .res 32
current_max: .res 32
next_min: .res 32
next_max: .res 32
last_min: .res 32
last_max: .res 32
initialized: .res 2
fx_dma_count: .res 2
fx_dma_bytes: .res 2
fx_dma_desc: .res 128       ; VRAM word address、byte length。最大32本。
.segment "CODE"
.a16
.i16
.if .defined(FX_FULL_TRANSFER) .or .defined(FX_GSU_CLIP)
fx_plan_dma:
  lda #1
  sta fx_dma_count
  stz fx_dma_desc
  lda #$3000
  sta fx_dma_desc+2
  sta fx_dma_bytes
  rts
fx_commit_dma:
fx_reset_next_bounds:
fx_add_next_bounds:
  rts
.else
fx_plan_dma:
  lda initialized
  bne :+
  ldx #30
  lda #$ffff
init_last:
  sta last_min,x
  dex
  dex
  bpl init_last
  inc initialized
:
  ldx #30
copy_next:
  lda next_min,x
  sta current_min,x
  lda next_max,x
  sta current_max,x
  dex
  dex
  bpl copy_next
  jmp union

; packet生成時のclip済み矩形を使い、次のGSU起動前に再走査しない。
fx_reset_next_bounds:
  ldx #30
  lda #$ffff
reset_next:
  sta next_min,x
  stz next_max,x
  dex
  dex
  bpl reset_next
  rts
fx_add_next_bounds:
  lda $0172
  lsr
  lsr
  lsr
  sta $01c4                 ; first column
  lda $0160
  clc
  adc $0172
  dec
  lsr
  lsr
  lsr
  sta $01c6                 ; last column
  lda $0174
  lsr
  lsr
  lsr
  sta $01c8                 ; first tile row
  lda $0162
  clc
  adc $0174
  dec
  lsr
  lsr
  lsr
  sta $01ca                 ; last tile row
  ldx $01c4
  sep #$20
columns:
  lda $01c8
  cmp next_min,x
  bcs :+
  sta next_min,x
:
  lda $01ca
  cmp next_max,x
  bcc :+
  sta next_max,x
:
  inx
  cpx $01c6
  bcc columns
  beq columns
  rep #$20
  rts
union:
  stz fx_dma_count
  stz fx_dma_bytes
  stz $01c4                 ; column tile base in VRAM words
  stz $01c6                 ; descriptor offset
  ldx #0
scan:
  sep #$20
  lda current_min,x
  cmp last_min,x
  bcc :+
  lda last_min,x
:
  cmp #$ff
  jeq no_column
  sta $01c8
  lda current_max,x
  cmp last_max,x
  bcs :+
  lda last_max,x
:
  sta $01ca
  rep #$20
  lda $01c8
  and #$ff
  asl
  asl
  asl
  clc
  adc $01c4
  sta $01cc
  lda $01ca
  and #$ff
  sec
  sbc $01c8
  inc
  asl
  asl
  asl
  asl
  sta $01ce
  ldy $01c6
  beq new_span
  ; 次の区間まで64byte以下なら、0の隙間も送ってDMA再設定を省く。
  lda fx_dma_desc-2,y
  lsr
  clc
  adc fx_dma_desc-4,y
  sta $01d0
  lda $01cc
  sec
  sbc $01d0
  cmp #33
  bcs new_span
  asl
  clc
  adc $01ce
  sta $01d0
  clc
  adc fx_dma_desc-2,y
  sta fx_dma_desc-2,y
  lda $01d0
  clc
  adc fx_dma_bytes
  sta fx_dma_bytes
  bra no_column
new_span:
  lda $01cc
  sta fx_dma_desc,y
  lda $01ce
  sta fx_dma_desc+2,y
  clc
  adc fx_dma_bytes
  sta fx_dma_bytes
  inc fx_dma_count
  iny
  iny
  iny
  iny
  sty $01c6
no_column:
  rep #$20
  lda $01c4
  clc
  adc #192                 ; 一列24 tiles ×8 words
  sta $01c4
  inx
  cpx #32
  jne scan
  ; 多数の細切れDMAより全FBの方が安い場合には一本へまとめる。
  lda fx_dma_count
  asl
  asl
  asl
  asl
  asl
  asl
  clc
  adc fx_dma_bytes
  cmp #12000
  bcc complete
  lda #1
  sta fx_dma_count
  stz fx_dma_desc
  lda #$3000
  sta fx_dma_desc+2
  sta fx_dma_bytes
complete:
  rts
fx_commit_dma:
  ldx #30
copy:
  lda current_min,x
  sta last_min,x
  lda current_max,x
  sta last_max,x
  dex
  dex
  bpl copy
  rts
.endif
