; 画面端の幅32byte以下は、行ごとのDMA設定を避けて内部RAMの専用ループで退避する。
.setcpu "65816"
.smart
.macpack longbranch
.import sa1_dma_try_begin: far, sa1_dma_end: far
.export sa1_small_edge_prepare: far, sa1_small_edge_save: far, sa1_small_edge_restore: far
.segment "BOOT"
sa1_small_edge_prepare:
  rep #$30
  lda $c4
  jeq small_prepare_done
  cmp #33
  jcs small_prepare_done
  inc
  and #$fffe
  sta $c4
  lda $c6
  beq :+
  lda #128
  sec
  sbc $c4
  sta $c6
:
  lda #512
  ldy #0
small_chunk_limit:
  sec
  sbc $c4
  bcc small_chunk_ready
  iny
  cpy #22
  bcc small_chunk_limit
small_chunk_ready:
  dey
  dey
  sty $da
  lda $c4
  lsr
  dec
  xba
  asl
  clc
  adc #.loword(small_templates)
  sta $f0
  jsl sa1_dma_try_begin
  bcc small_prepare_cpu
  lda #512
  sta $2238
  lda $f0
  sta $2232
  sep #$20
  lda #1
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0500
  sta $2235
  jsl sa1_dma_end
  bra small_patch_bank
small_prepare_cpu:
  phb
  ldx $f0
  ldy #$0500
  lda #511
  mvn #$01,#$00
  plb
small_patch_bank:
  sep #$20
  lda $0102
  ldx #0
small_patch_loop:
  sta $0507,x
  sta $060a,x
  .repeat 8
    inx
  .endrepeat
  cpx #128
  bcc small_patch_loop
  rep #$30
small_prepare_done:
  rtl
sa1_small_edge_save:
  rep #$30
  ldx $cc
  ldy $d8
  jsl $000500
  rtl
sa1_small_edge_restore:
  rep #$30
  ldx $cc
  ldy $d8
  jsl $000600
  rtl
.segment "GSU"
small_templates:
  .incbin "small_edge_templates.bin"
