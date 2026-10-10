; 起動時のVRAM画像をC2後半から展開し、C3を地面生成コードへ譲る。
.setcpu "65816"
.smart
.export compact_ppu_boot: far
.segment "GSU"
compact_ppu_boot:
  php
  phb
  sep #$20
  lda #0
  pha
  plb
  rep #$10
  ldx #0
  ldy #0
compact_packet:
  lda f:$c28000,x
  inx
  sta $02
  and #127
  inc
  sta $01
  lda $02
  bmi compact_repeat
compact_literal:
  lda f:$c28000,x
  inx
  jsr compact_put
  dec $01
  bne compact_literal
  bra compact_next
compact_repeat:
  lda f:$c28000,x
  inx
  sta $03
compact_repeat_byte:
  lda $03
  jsr compact_put
  dec $01
  bne compact_repeat_byte
compact_next:
  cpy #0
  bne compact_packet
  plb
  plp
  rtl
compact_put:
  sta $00
  tya
  and #1
  bne compact_high
  lda $00
  sta $2118
  iny
  rts
compact_high:
  lda $00
  sta $2119
  iny
  rts
