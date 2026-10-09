.setcpu "65816"
.smart
.import __SA1_LOAD__, __SA1_SIZE__
.export reset, probe_ready, probe_started, probe_finished
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
  ; 実ゲームと同じWRAM側でCPUを待機させ、ROMの空ポーリング競合を避ける。
  lda #$cb
  sta f:$7f0000
  lda #$6b
  sta f:$7f0001
.ifdef SA1_PRESCALED
  lda #4
  sta $2220
  inc
  sta $2221
  inc
  sta $2222
  inc
  sta $2223
.endif
  ldx #0
copy_sa1:
  lda f:__SA1_LOAD__,x
  sta $3200,x
  inx
  cpx #__SA1_SIZE__
  bcc copy_sa1
  rep #$20
  lda #$0200
  sta $2203
  stz $3100
  stz $3102
  stz $3104
  stz $3106
  sep #$20
  stz $2200
  lda #$80
  sta $4200
probe_ready:
  rep #$20
  lda $3100
  beq probe_ready
probe_started:
wait_sa1:
  lda $3104
  bne probe_finished
  jsl $7f0000
  bra wait_sa1
probe_finished:
  inc $3102
  stz $3100
release:
  lda $3104
  bne release
  bra probe_ready
nmi:
  php
  sep #$20
  pha
  lda $4210
  pla
  plp
  rti
.segment "HEADER"
  .res $10,0
  .byte "MONOSH SA1 4BPP PROBE"
  .byte $23,$34
.ifdef SA1_PRESCALED
  .byte $0d
.else
  .byte $0b
.endif
  .byte $08,$01,$33,$00
  .word $ffff,0
  .res $0a,0
  .word nmi
  .res $0e,0
  .word nmi,reset,nmi
