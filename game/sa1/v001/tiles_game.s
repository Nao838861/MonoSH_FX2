; 変更tileを32bit × 24行で保持し、二面分の差分から連続runだけを転送する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_tile_masks, sa1_tiles_transfer: far
.export sa1_tiles_clear: far
.segment "BOOT"
sa1_tile_masks:
.repeat 32,I
  .dword (1 << I)-1
.endrepeat
.dword $ffffffff
tmaskLo=$a0
tmaskHi=$a2
tbase=$a4
tbit=$a6
tstart=$a8
tactive=$aa
trow=$ac
tlength=$ae
tsource=$b0
tptr=$b8
tmode=$dc
sa1_tiles_clear:
  rep #$30
  stz tmode
  sep #$20
  lda #$84
  sta $2230
  rep #$20
  bra tiles_start
sa1_tiles_transfer:
  rep #$30
  lda #1
  sta tmode
  stz $0118
  stz $011a
  lda #$2000
  sta tptr
  sep #$20
  lda #$43
  sta tptr+2
  rep #$20
tiles_start:
  stz trow
  ldy #0
tiles_row:
  ldx trow
  lda f:$431800,x
  sta tmaskLo
  lda f:$431802,x
  sta tmaskHi
  lda tmode
  beq tiles_current_only
  lda $0116
  cmp #3
  bcc tiles_save
  lda f:$431880,x
  ora tmaskLo
  sta tmaskLo
  lda f:$431882,x
  ora tmaskHi
  sta tmaskHi
tiles_save:
  lda f:$431800,x
  sta f:$431880,x
  lda f:$431802,x
  sta f:$431882,x
tiles_current_only:
  lda tmaskLo
  ora tmaskHi
  jeq tiles_next_row
  ; 3tile以下の隙間はdescriptor設定より安いのでまとめて送る。
  lda tmaskLo
  sta $b0
  sta $bc
  lda tmaskHi
  sta $b2
  sta $be
  .repeat 3
    asl $bc
    rol $be
    lda $bc
    ora $b0
    sta $b0
    lda $be
    ora $b2
    sta $b2
  .endrepeat
  lda $b0
  sta $b4
  lda $b2
  sta $b6
  .repeat 3
    lsr $b2
    ror $b0
    lda $b0
    and $b4
    sta $b4
    lda $b2
    and $b6
    sta $b6
  .endrepeat
  lda $b4
  ora tmaskLo
  sta tmaskLo
  lda $b6
  ora tmaskHi
  sta tmaskHi
  txa
  xba
  sta tbase
  stz tbit
  stz tactive
tiles_bit:
  lsr tmaskHi
  ror tmaskLo
  bcc tiles_off
  lda tactive
  bne tiles_next_bit
  lda tbit
  sta tstart
  inc tactive
  bra tiles_next_bit
tiles_off:
  lda tactive
  beq tiles_next_bit
  jsr tiles_flush
  stz tactive
tiles_next_bit:
  inc tbit
  lda tmaskLo
  ora tmaskHi
  beq tiles_last_bit
  lda tbit
  cmp #32
  bcc tiles_bit
tiles_last_bit:
  lda tactive
  beq tiles_next_row
  jsr tiles_flush
tiles_next_row:
  lda trow
  clc
  adc #4
  sta trow
  cmp #96
  jne tiles_row
  rtl
tiles_flush:
  lda tmode
  jeq tiles_clear_run
  lda tbit
  sec
  sbc tstart
  .repeat 5
    asl
  .endrepeat
  sta tlength
  sta [tptr],y
  clc
  adc $0118
  sta $0118
  iny
  iny
  lda tstart
  .repeat 5
    asl
  .endrepeat
  clc
  adc tbase
  sta [tptr],y
  iny
  iny
  lsr
  sta [tptr],y
  iny
  iny
  inc $011a
  rts
tiles_clear_run:
  lda tbit
  sec
  sbc tstart
  asl
  asl
  sta tsource
  lda #$8000
  sta $2232
  sep #$20
  lda #2
  sta $2234
  rep #$20
  lda tstart
  asl
  asl
  clc
  adc tbase
  sta tlength
  ldx #8
tiles_clear_line:
  lda tsource
  sta $2238
  lda tlength
  sta $2235
  sep #$20
  lda #$40
  sta $2237
  rep #$20
  lda tlength
  clc
  adc #128
  sta tlength
  dex
  bne tiles_clear_line
  rts
