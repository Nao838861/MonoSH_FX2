; 表示方法を変えず、current|prev1の転送list/prefixをS-CPUで作る費用を測る。
.setcpu "65816"
.smart
.macpack longbranch
.import pipe_records
.export fp_probe_begin: far, fp_probe_masks: far, fp_probe_ready: far, fp_probe_return: far
.export fp_current, fp_previous, fp_descriptors, fp_prefix
.exportzp fp_generation, fp_count, fp_bytes, fp_cost, fp_gap, fp_source_base
.segment "ZEROPAGE"
fp_mask: .res 2
fp_index: .res 2
fp_base: .res 2
fp_start: .res 2
fp_end: .res 2
fp_length: .res 2
fp_count: .res 2
fp_bytes: .res 2
fp_last_end: .res 2
fp_output: .res 2
fp_gap: .res 2
fp_source_base: .res 2
fp_generation: .res 2
fp_cost: .res 2
fp_scratch: .res 2
.segment "COLORBSS"
fp_current: .res 96
fp_previous: .res 96
fp_descriptors: .res 288
fp_prefix: .res 192
; C2全体は起動時にWRAMへコピーされ、余白でBSSもゼロ初期化する。
; そこには追加せず、実際に対応する01:xxxxのROMから実行する。
.segment "GSU"
.a16
.i16
fp_probe_begin:
  php
  rep #$30
  pha
  phx
  phy
  phb
  phd
  lda #0
  tcd
  lda pipe_records,x
  and #$8400
  sta fp_source_base
  lda pipe_records+8,x
  sta fp_generation
  cmp #1
  bne fp_initialized
  ldx #94
fp_initialize:
  stz fp_previous,x
  dex
  dex
  bpl fp_initialize
fp_initialized:
  ; 先行SA-1はcollectのack前に次のmaskを書き始めない。
  lda #fp_current
  sta f:$002181
  lda #96
  sta f:$004305
  lda #$2800
  sta f:$004302
  lda #$8000
  sta f:$004300
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
  nop
  nop
  .ifdef FP_SAMPLE
  ; transfer_mask_captureが更新した2980は今回の一世代前の占有mask。
  lda #fp_previous
  sta f:$002181
  lda #96
  sta f:$004305
  lda #$2980
  sta f:$004302
  sep #$20
  lda #0
  sta f:$002183
  lda #1
  sta f:$00420b
  rep #$30
  nop
  nop
  .endif
fp_probe_masks:
  lda #1
  sta fp_gap
fp_restart:
  stz fp_count
  stz fp_bytes
  lda #4
  sta fp_index
  lda #1024
  sta fp_base
fp_word:
  ldx fp_index
  lda fp_current,x
  ora fp_previous,x
  and #255
  sta fp_mask
  beq fp_next_byte
fp_run:
  lda fp_mask
  asl
  tax
  lda f:fp_first,x
  clc
  adc fp_base
  sta fp_start
  lda f:fp_length_table,x
  clc
  adc fp_start
  sta fp_end
  jsr fp_flush
  bcc fp_retry
  ldx fp_mask
  lda f:fp_rest,x
  and #255
  sta fp_mask
  bne fp_run
fp_next_byte:
  lda fp_base
  clc
  adc #256
  sta fp_base
  inc fp_index
  lda fp_index
  cmp #96
  bcc fp_word
  bra fp_make_prefix
fp_retry:
  lda fp_gap
  clc
  adc #64
  sta fp_gap
  jmp fp_restart

fp_make_prefix:
  stz fp_bytes
  stz fp_cost
  stz fp_index
  ldx #0
  ldy #0
fp_prefix_next:
  lda fp_index
  cmp fp_count
  bcs fp_probe_ready
  lda fp_descriptors,x
  sta fp_length
  clc
  adc fp_bytes
  sta fp_bytes
  sta fp_prefix,y
  lda fp_length
  .repeat 5
    lsr
  .endrepeat
  sta fp_scratch
  lsr
  lsr
  clc
  adc fp_scratch
  adc fp_length
  adc #57
  adc fp_cost
  sta fp_cost
  sta fp_prefix+2,y
  txa
  clc
  adc #6
  tax
  iny
  iny
  iny
  iny
  inc fp_index
  bra fp_prefix_next
fp_probe_ready:
  ldx #94
fp_remember:
  lda fp_current,x
  sta fp_previous,x
  dex
  dex
  bpl fp_remember
  pld
  plb
  ply
  plx
  pla
  plp
fp_probe_return:
  rtl

fp_flush:
  lda fp_end
  sec
  sbc fp_start
  sta fp_length
  lda fp_count
  beq fp_new
  lda fp_start
  sec
  sbc fp_last_end
  cmp fp_gap
  bcs fp_new
  clc
  adc fp_length
  sta fp_length
  clc
  adc fp_bytes
  sta fp_bytes
  ldx fp_output
  lda fp_descriptors,x
  clc
  adc fp_length
  sta fp_descriptors,x
  lda fp_end
  sta fp_last_end
  sec
  rts
fp_new:
  lda fp_count
  cmp #48
  bcc :+
  clc
  rts
:
  asl
  sta fp_output
  asl
  clc
  adc fp_output
  sta fp_output
  tax
  lda fp_length
  sta fp_descriptors,x
  clc
  adc fp_bytes
  sta fp_bytes
  lda fp_start
  clc
  adc fp_source_base
  sta fp_descriptors+2,x
  lda fp_start
  lsr
  sec
  sbc #496
  sta fp_descriptors+4,x
  lda fp_end
  sta fp_last_end
  inc fp_count
  sec
  rts
.assert .bankbyte(fp_probe_begin)=.bankbyte(*-1), error, "front probe crosses a ROM bank"
.include "fixed_front_tables.inc"
