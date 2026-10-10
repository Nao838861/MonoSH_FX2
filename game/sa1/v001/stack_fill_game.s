; DMA engine使用中は、D=0をPHDでBW-RAMへ押して2Bずつ消す。
; 一行だけSA-1のstackをBW mirrorへ置く。割り込みを止めてから必ず戻す。
.setcpu "65816"
.smart
.export sa1_stack_clear_line: far
.export sa1_stack_clear_band: far
.export sa1_stack_clear_prepare: far
.export sa1_clear_wide_band: far
.segment "BOOT"
; 幅104byte以上の占有帯は、零である余白も含めた1KiBを一括消去する。
; compiled-ground配置の03:F000..F3FFは零専用領域。
sa1_clear_wide_band:
  sep #$20
  lda #$84
  sta $2230
  lda #3
  sta $2234
  rep #$20
  lda #1024
  sta $2238
  lda #$f000
  sta $2232
  lda $e6
  and #$fc00
  sta $2235
  sep #$20
  lda $0102
  sta $2237
  rep #$20
  rtl

sa1_stack_clear_prepare:
  rep #$30
  phb
  ldx #.loword(stack_band_body)
  ldy #$0300
  lda #67
  mvn #$00,#$00
  plb
  rtl

sa1_stack_clear_band:
  php
  sei
  rep #$30
  tsc
  sta $fc
  lda $0102
  sec
  sbc #$40
  asl
  asl
  asl
  sta $fa
  lda $e6
  xba
  and #$00e0
  .repeat 5
    lsr
  .endrepeat
  clc
  adc $fa
  sep #$20
  sta $2225
  rep #$20
  lda $ea
  lsr
  sta $fa
  lda #$0340
  sec
  sbc $fa
  sta $07f1
  lda #128
  sec
  sbc $ea
  sta $f8
  lda #8
  sta $f6
  lda $e6
  and #$1fff
  clc
  adc #$6000+7*128
  adc $ea
  dec
  tcs
  jmp ($07f1)
stack_band_body:
  .repeat 64
    phd
  .endrepeat
  jml stack_band_continue
stack_band_continue:
  dec $f6
  beq stack_band_done
  tsc
  sec
  sbc $f8
  tcs
  jmp ($07f1)
stack_band_done:
  lda $fc
  tcs
  sep #$20
  stz $2225
  rep #$20
  plp
  rtl

sa1_stack_clear_line:
  php
  sei
  rep #$30
  tsc
  sta $fc
  lda $0102
  sec
  sbc #$40
  asl
  asl
  asl
  sta $fa
  lda $e6
  xba
  and #$00e0
  .repeat 5
    lsr
  .endrepeat
  clc
  adc $fa
  sep #$20
  sta $2225
  rep #$20
  lda $ea
  lsr
  sta $fa
  lda #.loword(stack_clear_body)+64
  sec
  sbc $fa
  sta $07f1
  lda $e6
  and #$1fff
  clc
  adc #$6000
  adc $ea
  dec
  tcs
  jmp ($07f1)
stack_clear_body:
  .repeat 64
    phd
  .endrepeat
  lda $fc
  tcs
  sep #$20
  stz $2225
  rep #$20
  plp
  rtl
