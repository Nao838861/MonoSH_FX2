; 消去用の外接範囲は維持し、PPU転送だけを変更tileのbit集合へ絞る。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_prepare_transfer: far, sa1_merge_dma: far
.export sa1_transfer_mask_capture: far, sa1_transfer_mask_prepare: far
.segment "BOOT"
tmMask=$e0
tmBits=$e2
tmPosition=$e4
tmStart=$e6
tmActive=$e8
tmCount=$ea
tmBytes=$ec
tmEnd=$ee
tmOutput=$f0
tmLength=$f2
tmIndex=$f4

sa1_transfer_mask_capture:
  rep #$30
  ldx #0
  lda $0116
  bne tm_capture
tm_init:
  lda #0
  sta f:$436880,x
  .ifdef SA1_OCCUPANCY
  sta f:$436980,x
  .endif
  inx
  inx
  cpx #96
  bcc tm_init
  ldx #0
tm_capture:
  lda f:$436800,x
  .ifndef SA1_CHANGED_MASK
  .ifdef SA1_OCCUPANCY
  ora f:$436980,x
  .else
  ora f:$436880,x
  .endif
  .endif
  sta f:$436900,x
  .ifdef SA1_OCCUPANCY
  lda f:$436880,x
  sta f:$436980,x
  .endif
  lda f:$436800,x
  sta f:$436880,x
  inx
  inx
  cpx #96
  bcc tm_capture
  rtl

sa1_transfer_mask_prepare:
  rep #$30
  stz tmCount
  stz tmBytes
  stz tmPosition
  .ifdef SA1_VISIBLE_MASK
  lda #4
  sta tmIndex
  lda #1024
  sta $f6
  .else
  stz tmIndex
  stz $f6
  .endif
tm_word:
  ldx tmIndex
  lda f:$436900,x
  and #255
  sta tmMask
  beq tm_next_byte
tm_run:
  lda tmMask
  asl
  tax
  lda f:tm_first,x
  clc
  adc $f6
  sta tmStart
  lda f:tm_length,x
  clc
  adc tmStart
  sta tmPosition
  jsr tm_flush
  jcc tm_fallback
  ldx tmMask
  lda f:tm_rest,x
  and #255
  sta tmMask
  bne tm_run
tm_next_byte:
  lda $f6
  clc
  adc #256
  sta $f6
  inc tmIndex
  lda tmIndex
  cmp #96
  bcc tm_word
tm_done:
  lda tmCount
  sta $011a
  lda tmBytes
  sta $0118
  rtl
tm_fallback:
  .ifdef SA1_FRONT_MASK
  ; 表示面は二世代前の帯へfallbackできない。全面として予算判定で止める。
  lda #24576
  sta f:$430800
  sta $0118
  lda #0
  sta f:$430802
  sta f:$430804
  lda #1
  sta $011a
  rtl
  .else
  ; metadata一枠は24descriptorまで。必ず収まる既存の24帯へ戻す。
  jsl sa1_prepare_transfer
  jsl sa1_merge_dma
  rtl
  .endif

tm_flush:
  lda tmPosition
  sec
  sbc tmStart
  sta tmLength
  lda tmCount
  beq tm_new
  lda tmStart
  sec
  sbc tmEnd
  cmp #65
  bcs tm_new
  clc
  adc tmLength
  sta tmLength
  clc
  adc tmBytes
  sta tmBytes
  ldx tmOutput
  lda f:$430800,x
  clc
  adc tmLength
  sta f:$430800,x
  lda tmPosition
  sta tmEnd
  sec
  rts
tm_new:
  lda tmCount
  cmp #48
  bcc :+
  clc
  rts
:
  asl
  sta tmOutput
  asl
  clc
  adc tmOutput
  sta tmOutput
  tax
  lda tmLength
  sta f:$430800,x
  clc
  adc tmBytes
  sta tmBytes
  lda tmStart
  sta f:$430802,x
  lsr
  sta f:$430804,x
  lda tmPosition
  sta tmEnd
  inc tmCount
  sec
  rts

tm_first:
  .word 0,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 160,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 192,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 160,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 224,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 160,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 192,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 160,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0
  .word 128,0,32,0,64,0,32,0,96,0,32,0,64,0,32,0

tm_length:
  .word 0,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 32,32,32,64,32,32,64,96,64,32,32,64,96,32,128,160
  .word 32,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 64,32,32,64,32,32,64,96,96,32,32,64,128,32,160,192
  .word 32,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 32,32,32,64,32,32,64,96,64,32,32,64,96,32,128,160
  .word 64,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 96,32,32,64,32,32,64,96,128,32,32,64,160,32,192,224
  .word 32,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 32,32,32,64,32,32,64,96,64,32,32,64,96,32,128,160
  .word 32,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 64,32,32,64,32,32,64,96,96,32,32,64,128,32,160,192
  .word 64,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 32,32,32,64,32,32,64,96,64,32,32,64,96,32,128,160
  .word 96,32,32,64,32,32,64,96,32,32,32,64,64,32,96,128
  .word 128,32,32,64,32,32,64,96,160,32,32,64,192,32,224,256

tm_rest:
  .byte 0,0,0,0,0,4,0,0,0,8,8,8,0,12,0,0
  .byte 0,16,16,16,16,20,16,16,0,24,24,24,0,28,0,0
  .byte 0,32,32,32,32,36,32,32,32,40,40,40,32,44,32,32
  .byte 0,48,48,48,48,52,48,48,0,56,56,56,0,60,0,0
  .byte 0,64,64,64,64,68,64,64,64,72,72,72,64,76,64,64
  .byte 64,80,80,80,80,84,80,80,64,88,88,88,64,92,64,64
  .byte 0,96,96,96,96,100,96,96,96,104,104,104,96,108,96,96
  .byte 0,112,112,112,112,116,112,112,0,120,120,120,0,124,0,0
  .byte 0,128,128,128,128,132,128,128,128,136,136,136,128,140,128,128
  .byte 128,144,144,144,144,148,144,144,128,152,152,152,128,156,128,128
  .byte 128,160,160,160,160,164,160,160,160,168,168,168,160,172,160,160
  .byte 128,176,176,176,176,180,176,176,128,184,184,184,128,188,128,128
  .byte 0,192,192,192,192,196,192,192,192,200,200,200,192,204,192,192
  .byte 192,208,208,208,208,212,208,208,192,216,216,216,192,220,192,192
  .byte 0,224,224,224,224,228,224,224,224,232,232,232,224,236,224,224
  .byte 0,240,240,240,240,244,240,240,0,248,248,248,0,252,0,0
