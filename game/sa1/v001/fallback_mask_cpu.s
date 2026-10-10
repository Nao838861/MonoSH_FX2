; 裏ページに残る占有tileと今回の占有tileだけを転送する。
.setcpu "65816"
.smart
.macpack longbranch
.export fallback_init: far, fallback_collect: far, fallback_publish: far, fallback_prepare: far
.export fallback_boot_clear: far
.import __FALLBACKCPU_LOAD__, __FALLBACKCPU_SIZE__
.import pipe_render_slot, pipe_target_slot, pipe_records, pipe_record_offset
.import tm_first: far, tm_length: far, tm_rest: far
.segment "COLORBSS"
fbMasks: .res 128*8
fbPages: .res 128*2
fbCombined: .res 96
.segment "ZEROPAGE"
fbSlot: .res 2
fbPage: .res 2
fbMask: .res 2
fbStart: .res 2
fbEnd: .res 2
fbPosition: .res 2
fbActive: .res 2
fbCount: .res 2
fbBytes: .res 2
fbLength: .res 2
fbIndex: .res 2
fbBase: .res 2
fbOutput: .res 2
.segment "FALLBACKCPU"
fallback_boot_clear:
  rep #$30
  ; 起動時のROM全量複写でBSSへ入ったhelperコードだけを零へ戻す。
  .assert .loword(__FALLBACKCPU_LOAD__)+$2000+__FALLBACKCPU_SIZE__ <= $a000, error, "helper image crosses BSS"
  ldx #(__FALLBACKCPU_SIZE__+1)&$fffe
  lda #0
fb_boot_zero:
  dex
  dex
  sta f:$7e2000+.loword(__FALLBACKCPU_LOAD__),x
  bne fb_boot_zero
  rtl
fallback_init:
  rep #$30
  ldx #254
fb_init_word:
  stz fbPages,x
  dex
  dex
  bpl fb_init_word
  rtl
fallback_collect:
  rep #$30
  phx
  phy
  lda pipe_render_slot
  .repeat 7
    asl
  .endrepeat
  clc
  adc #fbMasks+4
  sta f:$002181
  lda #$8000
  sta f:$004300
  lda #$2804
  sta f:$004302
  lda #92
  sta f:$004305
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
  ply
  plx
  rtl
fallback_publish:
  rep #$30
  phx
  phy
  lda pipe_target_slot
  .repeat 7
    asl
  .endrepeat
  tay
  lda pipe_records+6,x
  beq :+
  lda #128
:
  tax
  .repeat 46,I
  lda fbMasks+4+I*2,y
  sta fbPages+4+I*2,x
  .endrepeat
  ply
  plx
  rtl
fallback_prepare:
  rep #$30
  lda pipe_target_slot
  .repeat 7
    asl
  .endrepeat
  sta fbSlot
  lda pipe_records+6,x
  beq :+
  lda #128
:
  sta fbPage
  tax
  ldy fbSlot
  .repeat 46,I
  lda fbMasks+4+I*2,y
  ora fbPages+4+I*2,x
  sta fbCombined+4+I*2
  .endrepeat
  lda #65
  sta fbActive
fb_restart:
  stz fbCount
  stz fbBytes
  stz fbEnd
  lda #4
  sta fbIndex
  lda #1024
  sta fbBase
fb_word:
  ldx fbIndex
  lda fbCombined,x
  and #255
  sta fbMask
  beq fb_next_byte
fb_run:
  lda fbMask
  asl
  tax
  lda f:tm_first,x
  clc
  adc fbBase
  sta fbStart
  lda f:tm_length,x
  clc
  adc fbStart
  sta fbPosition
  jsr fb_flush
  bcc fb_more_merge
  ldx fbMask
  lda f:tm_rest,x
  and #255
  sta fbMask
  bne fb_run
fb_next_byte:
  lda fbBase
  clc
  adc #256
  sta fbBase
  inc fbIndex
  lda fbIndex
  cmp #96
  bcc fb_word
  ldx pipe_record_offset
  lda fbBytes
  sta pipe_records+34,x
  lda fbCount
  asl
  sta fbCount
  asl
  clc
  adc fbCount
  sta pipe_records+2,x
  stz pipe_records+4,x
  rtl
fb_more_merge:
  lda fbActive
  clc
  adc #64
  sta fbActive
  jmp fb_restart
fb_flush:
  lda fbPosition
  sec
  sbc fbStart
  sta fbLength
  lda fbCount
  beq fb_new
  lda fbStart
  sec
  sbc fbEnd
  cmp fbActive
  bcs fb_new
  clc
  adc fbLength
  sta fbLength
  clc
  adc fbBytes
  sta fbBytes
  ldx fbOutput
  lda pipe_records,x
  clc
  adc fbLength
  sta pipe_records,x
  lda fbPosition
  sta fbEnd
  sec
  rts
fb_new:
  lda fbCount
  cmp #48
  bcc :+
  clc
  rts
:
  asl
  sta fbOutput
  asl
  clc
  adc fbOutput
  adc pipe_record_offset
  adc #208
  sta fbOutput
  tax
  lda fbLength
  sta pipe_records,x
  clc
  adc fbBytes
  sta fbBytes
  lda fbStart
  lsr
  sta pipe_records+4,x
  ldy pipe_record_offset
  lda pipe_records,y
  and #$8400
  clc
  adc fbStart
  sta pipe_records+2,x
  lda fbPosition
  sta fbEnd
  inc fbCount
  sec
  rts
