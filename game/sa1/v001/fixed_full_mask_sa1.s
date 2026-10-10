; 現在の占有maskだけで固定配置の全mapを作る。差分探索を省き、16tileを展開する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_sparse_map_prepare: far
.segment "GSU"
maskBits=$a2
maskWord=$a4
sa1_sparse_map_prepare:
  rep #$30
  lda #$ffff
  sta f:$434660
  lda #4
  sta maskWord
  ldx #0
  ldy #$2401
full_mask_word:
  phx
  ldx maskWord
  lda f:$432800,x
  sta maskBits
  plx
  .repeat 16
    lsr maskBits
    bcc :+
    tya
    bra :++
:
    lda #$2400
:
    sta f:$434000,x
    inx
    inx
    iny
  .endrepeat
  inc maskWord
  inc maskWord
  lda maskWord
  cmp #96
  jcc full_mask_word
  rtl
