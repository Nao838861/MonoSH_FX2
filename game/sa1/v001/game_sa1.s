; IRQ前後でworkerのDPとスタックを保存し、ゲーム専用BW40で実行する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_game_call: far
.export sa1_game_irq: far, sa1_game_begin, sa1_game_end
.segment "GSU"
.a16
.i16
sa1_game_irq:
  lda f:$0001a0
  cmp #1
  jne game_irq_done
  tsc
  sta f:$0001a4
  sep #$20
  lda #5
  sta $2225
  lda #$b1
  sta $2230
  rep #$30
  lda #2
  sta $011c
  lda #$7fff
  tcs
  ; worker DPを保存し、ゲームのcc65 DPを復元。
  ldx #0
  ldy #$a000
  lda #255
  mvn #$00,#$40
  ldx #0
  ldy #0
  lda #255
  mvn #$40,#$00
  sep #$20
  lda #$40
  pha
  plb
sa1_game_begin:
  jsl $c10000+sa1_game_call
  rep #$30
  ldx #0
  ldy #0
  lda #255
  mvn #$00,#$40
  ldx #$a000
  ldy #0
  lda #255
  mvn #$40,#$00
  rep #$30
  lda $011e
  bne :+
  stz $011c
:
  sep #$20
  stz $2225
  rep #$30
  lda f:$0001a4
  tcs
  lda #0
  sta f:$0001a0
sa1_game_end:
  sep #$20
  lda #$80
  sta $2209
  rep #$30
game_irq_done:
  rtl
