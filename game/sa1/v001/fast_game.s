.setcpu "65816"
.smart
.macpack longbranch
.export sa1_try_fast: far
.segment "BOOT"
ffirst=$a0
flast=$a2
foffset=$a4
fremaining=$a6
fchunk=$a8
fbytes=$aa
fsrc=$ac
fright=$b0
ftileEnd=$b2
fleft=$b4
spriteBase=$f8
sa1_try_fast:
  rep #$30
  lda $48                    ; rowx = floor(left / 2)
  bpl :+
  lda #0
:
  cmp #128
  jcs fast_empty
  sta fleft
  lda $38
  clc
  adc $34                    ; left + width
  jmi fast_empty
  cmp #257
  bcc :+
  lda #256
:
  inc
  lsr
  sta fright
  stz ffirst
  lda $3a                    ; top
  bpl :+
  lda #0
  sec
  sbc $3a
  sta ffirst
:
  lda #192
  sec
  sbc $3a
  cmp $36                    ; height
  bcc :+
  lda $36
:
  sta flast
  cmp ffirst
  jcc fast_empty
  jeq fast_empty
  clc
  adc $3a
  clc
  adc #7
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  sta ftileEnd
  lda ffirst
  clc
  adc $3a
  .repeat 3
    lsr
  .endrepeat
  asl
  asl
  tax
fast_tiles:
  lda $0120,x
  cmp fleft
  beq :+
  jcs fast_fail
:
  lda $0122,x
  cmp fright
  jcc fast_fail
  inx
  inx
  inx
  inx
  cpx ftileEnd
  bcc fast_tiles
  lda $3a
  .repeat 8
    asl
  .endrepeat
  clc
  adc $48
  clc
  adc #64
  sta spriteBase
  lda ffirst
  bne fast_chunks
  lda flast
  cmp $36
  bne fast_chunks
  lda $24                    ; rows = entire native row call chain
  sta $07f1
  sep #$20
  lda $26
  sta $07f3
  jsr fast_invoke
fast_empty:
  rep #$30
  sec
  rtl
fast_fail:
  clc
  rtl
fast_chunks:
  lda flast
  sec
  sbc ffirst
  sta fremaining
  lda ffirst
  asl
  sta foffset
  asl
  asl
  clc
  adc foffset
  adc ffirst                 ; 11 * first row
  clc
  adc $24
  sta fsrc
  sep #$20
  lda $26
  sta fsrc+2
  rep #$20
fast_chunk:
  lda fremaining
  cmp #21
  bcc :+
  lda #20
:
  sta fchunk
  asl
  sta fbytes
  asl
  asl
  clc
  adc fbytes
  adc fchunk
  sta fbytes
  sta $2238
  lda fsrc
  sta $2232
  sep #$20
  lda fsrc+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0700
  sta $2235
  sta $07f1
  sep #$20
  stz $07f3
  lda #$84
  sta $2230
  rep #$20
  ldx fbytes
  sep #$20
  lda #$6b
  sta $0700,x
  jsr fast_invoke
  rep #$20
  lda fsrc
  clc
  adc fbytes
  sta fsrc
  lda fremaining
  sec
  sbc fchunk
  sta fremaining
  jne fast_chunk
  sec
  rtl
fast_invoke:
  .a8
  lda #$40
  pha
  plb
  rep #$20
  jsr $07f0
  sep #$20
  lda #0
  pha
  plb
  rts
