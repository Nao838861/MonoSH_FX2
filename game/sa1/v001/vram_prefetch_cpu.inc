; p3Queueは転送済みの二枚まで。現在の部分転送面はpipe_target_slotが持つ。
p3Complete:
  lda pipe_target_slot
  pha
  asl
  tax
  lda #5
  sta pipe_status,x
  lda p3Tail
  asl
  tax
  pla
  sta p3Queue,x
  lda p3Tail
  eor #1
  sta p3Tail
  inc p3Count
  lda p3Count
  sta pipe_complete
  lda #$ffff
  sta pipe_target_slot
  lda pipe_read_slot
  inc
  cmp #SA1_PIPELINE_DEPTH
  bcc :+
  lda #0
:
  sta pipe_read_slot
  lda p3NextPage
  clc
  adc #$2000
  cmp #$6000
  bcc :+
  lda #0
:
  sta p3NextPage
  rts
p3Flip:
  .ifdef SA1_VRAM_PREFILL_COUNT
  .if SA1_VRAM_PREFILL_COUNT > 1
  lda fx4_generation
  bne :+
  lda p3Count
  cmp #SA1_VRAM_PREFILL_COUNT
  bcs :+
  rts
:
  .endif
  .endif
  lda pipe_target_slot
  pha
  lda p3Head
  asl
  tax
  lda p3Queue,x
  sta pipe_target_slot
  jsr pipe_flip
  .ifdef SA1_LATE_FLIP
  lda p3Serial
  sta p3LastFlip
  .endif
  pla
  sta pipe_target_slot
  lda p3Head
  eor #1
  sta p3Head
  dec p3Count
  lda p3Count
  sta pipe_complete
  rts
.ifdef SA1_VRAM_PUMP
; stage完了時にも、実際の非表示期間内なら転送を進める。表示はVIRQだけで行う。
p3Pump:
  php
  rep #$30
  pha
  phx
  phy
  phd
  phb
  lda #0
  tcd
  sep #$20
  lda #$7e
  pha
  plb
  sei
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #203
  bcs p3PumpBlank
  cmp #21
  bcc p3PumpBlank
  rep #$30
  plb
  pld
  ply
  plx
  pla
  plp
  rts
p3PumpBlank:
  .export p3PumpBlank
  rep #$30
  lda #1
  sta p3Manual
  jmp pipe_irq_transfer
.endif
