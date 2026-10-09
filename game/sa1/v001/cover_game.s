.setcpu "65816"
.smart
.macpack longbranch
.export sa1_select_cover: far, sa1_cover_row: far
.segment "BOOT"
coverMode=$da
coverOwner=$dc
coverPacket=$de
coverArea=$d8
coverEnd=$ce
selectCount=$a0
selectIndex=$a2
selectSize=$a4
selectLeft=$a6
selectRight=$a8
selectFireCount=$aa
sa1_select_cover:
  rep #$30
  stz coverMode
  stz coverArea
  lda #$ffff
  sta coverOwner
  lda $0106
  sta selectCount
  stz selectIndex
  stz selectFireCount
  sep #$20
  stz $2250
  rep #$20
  ldx #0
select_loop:
  lda selectIndex
  cmp selectCount
  bcs select_done
  lda f:$430006,x
  and #255
  cmp #31
  bne select_next
  inc selectFireCount
  lda f:$430004,x
  sta selectSize
  and #255
  sta $2251
  lda selectSize
  xba
  and #255
  sta $2253
  nop
  nop
  lda $2306
  cmp coverArea
  bcc select_next
  sta coverArea
  lda selectIndex
  sta coverOwner
  stx coverPacket
select_next:
  txa
  clc
  adc #10
  tax
  inc selectIndex
  bra select_loop
select_done:
  lda selectFireCount
  cmp #3
  bcs select_enable
  lda #$ffff
  sta coverOwner
  rtl
select_enable:
  ; 一番大きい手前の画像の不透明区間だけを遮蔽判定に使う。
  sep #$20
  lda #$84
  sta $2230
  rep #$20
  lda #$8000
  sta $2232
  lda #384
  sta $2238
  stz $2235
  sep #$20
  lda #2
  sta $2234
  lda #$42
  sta $2237
  rep #$20
  rtl

sa1_cover_row:
  rep #$30
  lda $84                    ; codeptr。直前2バイトに不透明区間がある。
  sec
  sbc #2
  sta $60
  sep #$20
  lda $86
  sta $62
  rep #$20
  ldy #0
  lda [$60],y
  sta selectSize
  and #255
  clc
  adc $70                    ; rowx + origin
  sta selectLeft
  lda selectSize
  xba
  and #255
  clc
  adc $70
  sta selectRight
  bmi cover_done
  cmp #129
  bcc :+
  lda #128
  sta selectRight
:
  lda selectLeft
  bpl :+
  stz selectLeft
:
  lda selectLeft
  cmp selectRight
  bcs cover_done
  lda $44                    ; rowbase = y * 128
  .repeat 6
    lsr
  .endrepeat
  tax
  lda selectRight
  xba
  ora selectLeft
  sta f:$420000,x
cover_done:
  rtl
