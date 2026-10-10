; IRQ内で実行する短いSA-1 job。描画中のDPを保存し、専用の内部RAMを使う。
.setcpu "65816"
.smart
.export sa1_fallback_build: far
.export sa1_fallback_irq: far
.import tm_first: far, tm_length: far, tm_rest: far
.segment "GSU"
sbMask=$00
sbStart=$02
sbEnd=$04
sbPosition=$06
sbActive=$08
sbCount=$0a
sbBytes=$0c
sbLength=$0e
sbIndex=$10
sbBase=$12
sbOutput=$14
sbRawBase=$16
.a16
.i16
sa1_fallback_irq:
  lda a:$01a0
  cmp #1
  beq sa1_fallback_build
  rtl
sa1_fallback_build:
  rep #$30
  phd
  lda #$01a6
  tcd
  lda #65
  sta sbActive
sb_restart:
  stz sbCount
  stz sbBytes
  stz sbEnd
  lda #4
  sta sbIndex
  lda #1024
  sta sbBase
sb_word:
  ldx sbIndex
  lda f:$433400,x
  and #255
  sta sbMask
  beq sb_next_byte
sb_run:
  lda sbMask
  asl
  tax
  lda f:tm_first,x
  clc
  adc sbBase
  sta sbStart
  lda f:tm_length,x
  clc
  adc sbStart
  sta sbPosition
  jsr sb_flush
  bcc sb_more_merge
  ldx sbMask
  lda f:tm_rest,x
  and #255
  sta sbMask
  bne sb_run
sb_next_byte:
  lda sbBase
  clc
  adc #256
  sta sbBase
  inc sbIndex
  lda sbIndex
  cmp #96
  bcc sb_word
  lda sbCount
  sta a:$01a2
  lda sbBytes
  sta a:$01a4
  stz a:$01a0
  pld
  rtl
sb_more_merge:
  lda sbActive
  clc
  adc #64
  sta sbActive
  jmp sb_restart
sb_flush:
  lda sbPosition
  sec
  sbc sbStart
  sta sbLength
  lda sbCount
  beq sb_new
  lda sbStart
  sec
  sbc sbEnd
  cmp sbActive
  bcs sb_new
  clc
  adc sbLength
  sta sbLength
  clc
  adc sbBytes
  sta sbBytes
  ldx sbOutput
  lda f:$433500,x
  clc
  adc sbLength
  sta f:$433500,x
  lda sbPosition
  sta sbEnd
  sec
  rts
sb_new:
  lda sbCount
  cmp #48
  bcc :+
  clc
  rts
:
  asl
  sta sbOutput
  asl
  clc
  adc sbOutput
  sta sbOutput
  tax
  lda sbLength
  sta f:$433500,x
  clc
  adc sbBytes
  sta sbBytes
  lda sbStart
  lsr
  sta f:$433504,x
  lda sbRawBase
  clc
  adc sbStart
  sta f:$433502,x
  lda sbPosition
  sta sbEnd
  inc sbCount
  sec
  rts
