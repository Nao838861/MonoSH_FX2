; FX2カーネル検証用。GSU実行中のCPUコードはすべてWRAM。
.setcpu "65816"
.smart
.import __WRAM_LOAD__, __WRAM_SIZE__
.export reset, cpu_ready, cpu_started, cpu_finished, dma_started, dma_finished
.export dma_wait_vblank, dma_wait_frame, dma_wait_bottom, dma_wait_hblank

.segment "BOOT"
reset:
  sei
  clc
  xce
  rep #$30
  lda #$1FFF
  tcs
  sep #$20
  lda #$80
  sta $2100
  stz $4200
  stz $420C
  stz $420B
  lda #$FF
  sta $4201
  rep #$30
  ldx #.loword(__WRAM_LOAD__)
  ldy #$0000
  lda #__WRAM_SIZE__-1
  mvn #$00, #$7E
  pea $0000
  plb
  plb
  jml $7E0000

.segment "WRAM"
.a16
.i16
wram_main:
  sep #$20
  lda #$01
  sta $3039             ; CLSR: 21.48MHz、overclockなし
  sta $3033             ; BRAMR
  lda #$80
  sta $3037             ; IRQを無効化。fast multiplyは使わない
  lda #$08
  sta $3038             ; SCBR: FB=$702000
  stz $303C             ; RAM bank 0
  lda #$01
  sta $3034             ; GSU program bank 1
  lda #$38
  sta $303A             ; SCMR: H192, 2bpp, RON/RAN
  lda #$00
  sta f:$7E1F00
cpu_ready:
  lda #$10
  sta f:$7E1FF0
wait_request:
  lda f:$7E1F00
  beq wait_request
  cmp #$02
  bne start_gsu
  jmp dma_request
start_gsu:
  lda #$01
cpu_started:
  sta f:$7E1FF0
  rep #$30
  ldx #$0000
load_registers:
  lda f:$7E1F20,x
  sta $3000,x
  inx
  inx
  cpx #$001E
  bne load_registers
  lda f:$7E1F3E
  sta $301E             ; R15への書き込みで開始
  sep #$20
wait_gsu:
  lda $3030
  bit #$20
  bne wait_gsu
cpu_finished:
  lda #$02
  sta f:$7E1FF0
  lda #$00
  sta f:$7E1F00
  jmp cpu_ready

; 192行をHDMAで厳密に表示し、DMAがはみ出した場合に失われるVRAM byteを測る。
; command=2、$1F02=高さ、$1F04=転送bytes、$1100=INIDISP HDMA表。
dma_request:
  lda #$80
  sta $2100
  stz $420C
  stz $2105             ; Mode0
  stz $210B             ; BG2 CHR base=0
  lda #$40
  sta $2108             ; BG2 tilemap byte=$8000
  lda #$02
  sta $212C
  stz $212D
  stz $2133
  stz $2121
  stz $2122
  stz $2122             ; 背景色0=黒
  lda #$23
  sta $2121             ; BG2のcolor3
  lda #$FF
  sta $2122
  lda #$7F
  sta $2122
  lda #$80
  sta $2115
  rep #$30
  lda #$4000
  sta $2116
  lda #24
  sta $1E00
  sep #$20
  lda f:$7E1F02
  cmp #192
  beq dma_map_height_set
  rep #$20
  lda #28
  sta $1E00
  sep #$20
dma_map_height_set:
  rep #$30
  stz $1E04
dma_map_row:
  lda $1E04
  ora #$2000
  ldx #32
dma_map_column:
  sta $2118
  clc
  adc $1E00
  dex
  bne dma_map_column
  inc $1E04
  lda $1E04
  cmp #32
  bne dma_map_row
  ; 画像領域を0で初期化。mode1・source固定。
  stz $2116
  lda #$1809
  sta $4300
  lda #$1F01
  sta $4302
  lda f:$7E1F04
  sta $4305
  sep #$20
  lda #$7E
  sta $4304
  lda #$01
  sta $420B
  ; BG2のsource y=0を、有効領域の最初のscanlineへ置く。
  lda f:$7E1F02
  cmp #192
  beq dma_scroll_192
  lda #$FF
  bra dma_scroll_set
dma_scroll_192:
  lda #$EF
dma_scroll_set:
  sta $2110             ; BG2VOFS
  lda #$FF
  sta $2110
  stz $210F
  stz $210F
  ; HDMA channel1、通常DMA channel0。
  stz $4310
  stz $4311
  rep #$20
  lda #$1100
  sta $4312
  sep #$20
  lda #$7E
  sta $4314
  lda #$02
  sta $420C
dma_wait_vblank:
  lda $4212
  bpl dma_wait_vblank
dma_wait_frame:
  lda $4212
  bmi dma_wait_frame
  lda f:$7E1F02
  cmp #192
  beq dma_target_192
  lda #225
  bra dma_target_set
dma_target_192:
  lda #209
dma_target_set:
  sta $1E06
dma_wait_bottom:
  lda $213F             ; counter latchをlow byteへ戻す
  lda $2137             ; HV counterをlatch
  lda $213D
  cmp $1E06
  bne dma_wait_bottom
  ; HDMA表がbottomをblankにするのを待つ。HVBJOYのHBlankで位相を固定。
dma_wait_hblank:
  lda $4212
  and #$40
  beq dma_wait_hblank
  lda #$80
  sta $2100
  rep #$20
  stz $2116
  lda #$1801
  sta $4300
  lda #$2000
  sta $4302
  lda f:$7E1F04
  sta $4305
  sep #$20
  lda #$70
  sta $4304
  lda #$03
dma_started:
  sta f:$7E1FF0
  lda #$01
  sta $420B
  lda #$04
dma_finished:
  sta f:$7E1FF0
dma_capture_wait_vblank:
  lda $4212
  bpl dma_capture_wait_vblank
dma_capture_wait_frame:
  lda $4212
  bmi dma_capture_wait_frame
dma_capture_wait_line:
  lda $213F
  lda $2137
  lda $213D
  cmp #203
  bne dma_capture_wait_line
  lda #$05
  sta f:$7E1FF0
  lda #$00
  sta f:$7E1F00
  jmp cpu_ready

.segment "HEADER"
  .byte 0,0,"FX2P",0,0,0,0,0,0,0,$06,0,0
  .byte "MONOSH FX2 PROBE V001"
  .byte $20,$15,$09,$00,$01,$33,$00
  .word $FFFF,$0000
  .res $20,$00
  ; エミュレーションreset vector=$FFFC
