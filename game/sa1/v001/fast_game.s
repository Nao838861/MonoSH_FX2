.setcpu "65816"
.smart
.macpack longbranch
.export sa1_try_fast: far
.export sa1_draw_rows: far
.export fast_tiles, fast_fail, fast_base_ready
.import sa1_edge_prepare: far, sa1_edge_save: far, sa1_edge_restore: far
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
  stz $c4
  lda $c0
  and #255
  clc
  adc $38
  cmp #$8000
  ror                        ; floor((left + opaque left) / 2)
  bpl :+
  lda #0
:
  cmp #128
  jcs fast_empty
  sta fleft
  lda $c2
  and #255
  clc
  adc $38                    ; left + opaque right
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
  lda $3a
  .repeat 7
    asl
  .endrepeat
  clc
  adc $48
  sta spriteBase
  jsl sa1_edge_prepare
  lda $c3
  and #255
  cmp flast
  bcc :+
  lda flast
:
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
  lda $c1
  and #255
  cmp ffirst
  bcs :+
  lda ffirst
:
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
fast_base_ready:
  lda $c4
  bne fast_chunks
  lda flast
  cmp $36
  bne fast_chunks
  ; 上にはみ出す場合も、見える最初の行から末尾のRTLまで直接呼べる。
  ; 行の座標は元のdyを含むのでspriteBaseを補正する必要はない。
  lda ffirst
  asl
  sta foffset
  asl
  asl
  clc
  adc foffset
  adc ffirst
  clc
  adc $24
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
sa1_draw_rows:
  rep #$30
  sta ffirst
  stx flast
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
  ldx $c4
  beq :+
  cmp $da
  bcc :+
  lda $da
:
  sta fchunk
  jsl sa1_edge_save
  lda fchunk
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
  jsl sa1_edge_restore
  rep #$20
  lda fsrc
  clc
  adc fbytes
  sta fsrc
  lda fremaining
  sec
  sbc fchunk
  sta fremaining
  lda ffirst
  clc
  adc fchunk
  sta ffirst
  lda fremaining
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
