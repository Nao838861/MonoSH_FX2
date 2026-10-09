; タイル順で近接する転送をまとめ、descriptor設定より小さい隙間も送る。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_merge_dma: far
.segment "BOOT"
mremain=$a0
msource=$a2
mdest=$a4
mend=$a6
mgap=$a8
madd=$aa
mcount=$ac
mptr=$b8
sa1_merge_dma:
  rep #$30
  lda $011a
  jeq merge_done
  dec
  sta mremain
  lda #1
  sta mcount
  stz mdest
  lda #6
  sta msource
  lda #$0800
  sta mptr
  sep #$20
  lda #$43
  sta mptr+2
  rep #$20
merge_next:
  lda mremain
  beq merge_publish
  ldx mdest
  lda f:$430802,x
  clc
  adc f:$430800,x
  sta mend
  ldx msource
  lda f:$430802,x
  sec
  sbc mend
  sta mgap
  cmp #193
  bcs merge_separate
  clc
  adc $0118
  sta $0118
  lda f:$430800,x
  clc
  adc mgap
  sta madd
  ldx mdest
  lda f:$430800,x
  clc
  adc madd
  sta f:$430800,x
  bra merge_advance
merge_separate:
  lda mdest
  clc
  adc #6
  sta mdest
  tay
  lda f:$430800,x
  sta [mptr],y
  iny
  iny
  lda f:$430802,x
  sta [mptr],y
  iny
  iny
  lda f:$430804,x
  sta [mptr],y
  inc mcount
merge_advance:
  lda msource
  clc
  adc #6
  sta msource
  dec mremain
  bra merge_next
merge_publish:
  lda mcount
  sta $011a
merge_done:
  rtl
