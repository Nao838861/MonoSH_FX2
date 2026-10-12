; stack helperのROM原本03:E400をI-RAM0300へ配置して実行する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_stack_explosions_load: far
.import sa1_stack_explosions: far, __STACKBOOT_SIZE__
.import sa1_dma_try_begin: far, sa1_dma_end: far
.segment "GSU"
sa1_stack_explosions_load:
  rep #$30
  jsl sa1_dma_try_begin
  bcc stack_load_cpu
  lda #__STACKBOOT_SIZE__
  sta $2238
  lda #$e400
  sta $2232
  sep #$20
  lda #3
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  jml sa1_stack_explosions
stack_load_cpu:
  phb
  lda #__STACKBOOT_SIZE__-1
  ldx #$e400
  ldy #$0300
  mvn #$03,#$00
  plb
  jml sa1_stack_explosions
