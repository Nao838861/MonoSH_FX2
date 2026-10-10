; 次のSA-1描画を開始してから、S-CPUが前の配置表をWRAMへ作る。
.setcpu "65816"
.smart
.macpack longbranch
.import pipe_records,pipe_status
.export fifo_map_deferred: far
.segment "COLORBSS"
fmSlot: .res 2
fmRecord: .res 2
fmDesc: .res 2
fmEnd: .res 2
fmMap: .res 2
fmRaw: .res 2
fmCount: .res 2
fmTail: .res 2
fmTile: .res 2
.segment "CODE"
.a16
.i16
fifo_map_deferred:
  php
  phb
  rep #$30
  pha
  phx
  phy
  sep #$20
  lda #$7e
  pha
  plb
  rep #$20
  stz fmSlot
fm_find:
  ldx fmSlot
  lda pipe_status,x
  cmp #2
  jcc fm_next
  txa
  .repeat 8
    asl
  .endrepeat
  tax
  lda pipe_records+62,x
  jne fm_next
  lda #2
  sta pipe_records+62,x
  stx fmRecord
  lda pipe_records+60,x
  sta fmMap
  lda pipe_records,x
  and #$8400
  sta fmRaw
.ifdef SA1_FIFO_CPU_MAP_DMA
  php
  sei
  lda fmMap
  sta f:$002181
  lda #.loword(fmZeros)
  sta f:$004302
  lda #1472
  sta f:$004305
  lda #$8000
  sta f:$004300
  sep #$20
  lda #1
  sta f:$002183
  lda #.bankbyte(fmZeros)
  sta f:$004304
  lda #1
  sta f:$00420b
  plp
  rep #$30
.else
  phb
  sep #$20
  lda #$7f
  pha
  plb
  rep #$20
  lda f:$7e0000+fmMap
  tax
  ldy #46
  lda #$2400
fm_empty:
  .repeat 16,I
    sta a:I*2,x
  .endrepeat
  txa
  clc
  adc #32
  tax
  lda #$2400
  dey
  bne fm_empty
  plb
.endif
  ldx fmRecord
  lda pipe_records+2,x
  clc
  adc fmRecord
  adc #208
  sta fmEnd
  txa
  clc
  adc #208
  sta fmDesc
fm_descriptor:
  ldx fmDesc
  cpx fmEnd
  jcs fm_ready
  lda pipe_records,x
  .repeat 5
    lsr
  .endrepeat
  sta fmCount
  and #7
  sta fmTail
  lda pipe_records+2,x
  sec
  sbc fmRaw
  .repeat 4
    lsr
  .endrepeat
  sec
  sbc #64
  clc
  adc fmMap
  tay
  lda pipe_records+4,x
  .repeat 4
    lsr
  .endrepeat
  ora #$2400
  sta fmTile
  lda fmCount
  lsr
  lsr
  lsr
  tax
  phb
  sep #$20
  lda #$7f
  pha
  plb
  rep #$20
  lda f:$7e0000+fmTile
  cpx #0
  beq fm_remainder
fm_eight:
  .repeat 8,I
    sta a:I*2,y
    inc
  .endrepeat
  pha
  tya
  clc
  adc #16
  tay
  pla
  dex
  bne fm_eight
fm_remainder:
  pha
  lda f:$7e0000+fmTail
  tax
  pla
  cpx #0
  beq fm_descriptor_done
fm_word:
  sta a:0,y
  inc
  iny
  iny
  dex
  bne fm_word
fm_descriptor_done:
  plb
  lda fmDesc
  clc
  adc #6
  sta fmDesc
  jmp fm_descriptor
fm_ready:
  ldx fmRecord
  lda #1
  sta pipe_records+62,x
fm_next:
  lda fmSlot
  clc
  adc #2
  sta fmSlot
  cmp #24
  jcc fm_find
  ply
  plx
  pla
  plb
  plp
  rtl
.ifdef SA1_FIFO_CPU_MAP_DMA
.segment "GSU"
fmZeros:
  .repeat 736
    .word $2400
  .endrepeat
.endif
