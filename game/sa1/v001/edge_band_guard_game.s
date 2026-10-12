; 40/41の右はみ出しを、描画chunkと重なる8行alpha帯の外接幅に絞る。
; cache512Bの上限・元のchunk長は保持。左/反転/幅>32Bは従来経路。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_edge_band_init: far, sa1_edge_band_chunk: far
.segment "GSU"
ebOriginal=$01b2
ebActive=$01b4
ebTable=$01b6
ebBank=$01b8
ebPtr=$e0
ebFirst=$e4
ebEnd=$e6
ebMaximum=$e8
ebPosition=$ea
ebBounds=$ec
sa1_edge_band_init:
  rep #$30
  ; 呼出し側がoriginal/activeを設定し、C4>0の時だけ入る。
  cmp #33
  jcs eb_return
  lda $38
  jmi eb_return
  lda $3c
  bit #$30
  jne eb_return
  lda $3e
  cmp #40
  beq eb_select
  cmp #41
  jne eb_return
eb_select:
  lda $34
  cmp #32
  jcc eb_return
  lda $36
  cmp #24
  jcc eb_return
  lda $2c
  asl
  tax
  lda f:$433000,x
  tax
  lda f:$ff0007,x
  sta ebPtr
  lda f:$ff0009,x
  and #255
  sta ebPtr+2
  ldy #0
  lda [ebPtr],y
  pha
  ldy #2
  lda [ebPtr],y
  and #255
  sta ebBank
  pla
  sta ebTable
  lda #1
  sta ebActive
eb_return:
  rtl

sa1_edge_band_chunk:
  rep #$30
  ; 呼出し側でactiveを確認済み。
  lda ebTable
  sta ebPtr
  lda ebBank
  sta ebPtr+2
  lda $a0
  lsr
  lsr
  lsr
  sta ebFirst
  lda $a0
  clc
  adc $a8
  adc #7
  lsr
  lsr
  lsr
  sta ebEnd
  stz ebPosition
  stz ebMaximum
eb_scan:
  ldy #0
  lda [ebPtr],y
  sta ebBounds
  ldy #2
  lda [ebPtr],y
  and #255
  clc
  adc ebPosition
  sta ebPosition
  cmp ebFirst
  bcc eb_next
  beq eb_next
  lda ebBounds
  xba
  and #255
  cmp ebMaximum
  bcc :+
  sta ebMaximum
:
  lda ebPosition
  cmp ebEnd
  bcs eb_finish
eb_next:
  lda ebPtr
  clc
  adc #3
  sta ebPtr
  bra eb_scan
eb_finish:
  lda ebMaximum
  beq eb_zero
  clc
  adc $38
  cmp #257
  bcc eb_zero
  sec
  sbc #255
  lsr
  inc
  and #$fffe
  sta $c4
  rtl
eb_zero:
  stz $c4
  rtl
