; 二つの256px幅bitmapの中央128pxを、詰め直さずCC1→PPU DMAで連結する。
.setcpu "65816"
.smart
.import __SA1_LOAD__, __SA1_SIZE__
.export reset, probe_ready, split_transfer_begin, split_transfer_end, probe_finished
.segment "BOOT"
reset:
  sei
  clc
  xce
  rep #$30
  lda #$1fff
  tcs
  sep #$20
  lda #$80
  sta $2100
  sta $2226
  stz $2229
  stz $4200
  stz $420c
  ldx #0
copy_worker:
  lda f:__SA1_LOAD__,x
  sta $3200,x
  inx
  cpx #__SA1_SIZE__
  bcc copy_worker
  rep #$20
  lda #$0200
  sta $2203
  stz $3100
  stz $3104
  sep #$20
  stz $2200
probe_ready:
  rep #$30
  lda $3100
  beq probe_ready
wait_cc1:
  lda $3104
  beq wait_cc1
split_transfer_begin:
  sep #$20
  lda #$80
  sta $2115
  rep #$20
  stz $2116
  lda #$1801
  sta $4300
  sep #$20
  lda $3108
  sta $4304
  rep #$30
  ldx #$0500                 ; 0400 + 8 central tiles * 32B
  ldy #24
split_band:
  stx $4302
  lda #512
  sta $4305
  sep #$20
  lda #1
  sta $420b
  rep #$20
  txa
  clc
  adc #$8000                ; second bitmap, same conversion base and width
  sta $4302
  lda #512
  sta $4305
  sep #$20
  lda #1
  sta $420b
  rep #$20
  txa
  clc
  adc #1024
  tax
  dey
  bne split_band
  sep #$20
  lda #$95
  sta $2231
  rep #$20
split_transfer_end:
probe_finished:
  stz $3100
wait_release:
  lda $3104
  bne wait_release
  bra probe_ready
.segment "SA1"
worker:
  sei
  clc
  xce
  rep #$30
  lda #$01ff
  tcs
  lda #0
  tcd
  sep #$20
  pha
  plb
  lda #$80
  sta $2227
worker_wait:
  rep #$20
  lda $0100
  beq worker_wait
  sep #$20
  lda #$b1
  sta $2230
  lda #$15
  sta $2231
  rep #$20
  lda #$0400
  sta $2232
  sep #$20
  lda $0108
  sta $2234
  rep #$20
  lda #$07c0
  sta $2235                ; writing 2236 initializes CC1
  lda #1
  sta $0104
worker_release:
  lda $0100
  bne worker_release
  stz $0104
  bra worker_wait
.segment "HEADER"
  .res $10,0
  .byte "MONOSH SA1 SPLIT CC1 "
  .byte $23,$34,$0d,$08,$01,$33,$00
  .word $ffff,0
  .res $0a,0
  .word reset
  .res $0e,0
  .word reset,reset,reset
