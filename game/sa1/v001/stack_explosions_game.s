; 幅94の爆発40/41。逆順PEA描画を最大8行ずつ実行する。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_stack_explosions: far, sa1_stack_row_begin: far, sa1_stack_row_done: far
.segment "STACKBOOT"
srRows=$a0
srRecords=$a4
srRow=$a8
srLimit=$aa
srSaved=$ac
srCode=$ae
srHint=$b2
srOrigin=$b6
srEnd=$b8
srRawX=$ba
srMap=$bc
srBatch=$be
srGuard=$c0
srGuardPtr=$c2
srDest=$c6
srBank=$c8
srEntry=$cc
srMax=$ce
srJump=$d0
srTmp=$d4
srNextMap=$d6
sa1_stack_explosions:
  rep #$30
  lda $3e
  cmp #40
  beq :+
  cmp #41
  jne sr_no
:
  lda $34
  cmp #94
  jne sr_no
  lda $38
  jmi sr_no
  cmp #256
  jcs sr_no
  lda $3a
  bmi :+
  cmp #192
  jcs sr_no
:
  lda $3c
  and #$33
  jne sr_no
  lda $2c
  asl
  tax
  lda f:$433000,x
  sta srEntry
  ldx #0
sr_find:
  txa
  cmp #32
  jcs sr_no
  lda f:$df6fe5,x
  cmp srEntry
  beq sr_found
  txa
  clc
  adc #8
  tax
  bra sr_find
sr_found:
  lda $38
  and #1
  beq :+
  inx
  inx
  inx
:
  lda f:$df6fe7,x
  sta srRows
  sep #$20
  lda f:$df6fe9,x
  sta srRows+2
  rep #$20
  lda f:$df6fe2
  sta srRecords
  sep #$20
  lda f:$df6fe4
  sta srRecords+2
  rep #$20
  php
  sei
  tsc
  sta srSaved
  lda #$ffff
  sta srMap
  stz srBatch
  stz srRow
  lda $3a
  bpl :+
  eor #$ffff
  inc
  sta srRow
:
  lda #192
  sec
  sbc $3a
  cmp $36
  bcc :+
  lda $36
:
  sta srMax
  lda $38
  lsr
  sta srRawX
  lda #128
  sec
  sbc srRawX
  sta srLimit
  lda f:$000102
  and #255
  sta srBank
  sta srGuardPtr+2
  lda #.loword(sa1_stack_row_done)
  sta $0701
  sep #$20
  lda #$5c
  sta $0700
  lda #^sa1_stack_row_done
  sta $0703
  rep #$20
  jmp sr_next
sr_no:
  clc
  rtl

; ここへはraw描画先をSにしたままJMLで戻る。JSR/PHAは使わない。
sa1_stack_row_done:
  sep #$20
  lda srGuard
  sta [srGuardPtr]
  rep #$20
  dec srBatch
sr_advance:
  inc srRow
sr_next:
  lda srRow
  cmp srMax
  jcs sr_done
  asl
  tay
  lda [srRows],y
  tay
  lda [srRecords],y
  sta srCode
  iny
  iny
  lda [srRecords],y
  sta srCode+2
  iny
  lda [srRecords],y
  sta srHint
  iny
  iny
  lda [srRecords],y
  sta srHint+2
  iny
  lda [srRecords],y
  sta srOrigin
  and #255
  cmp srLimit
  jcs sr_advance
  lda srLimit
  sec
  sbc srOrigin
  ; srOriginの上位byteはextentなので、減算後に低byteだけ取る。
  and #255
  sta srTmp
  lda srOrigin+1
  and #255
  cmp srTmp
  bcc :+
  lda srTmp
:
  inc
  and #$fffe
  tay
  lda [srHint],y
  sta srTmp
  xba
  and #255
  sta srEnd
  jeq sr_advance
  lda srTmp
  and #255
  clc
  adc srCode
  sta srJump
  sep #$20
  lda srCode+2
  sta srJump+2
  rep #$20
  lda srRow
  clc
  adc $3a
  .repeat 7
    asl
  .endrepeat
  clc
  adc f:$00019a
  sta srDest
  clc
  adc #128
  sta srGuardPtr
  sep #$20
  lda [srGuardPtr]
  sta srGuard
  rep #$20
  lda srOrigin
  and #255
  clc
  adc srRawX
  clc
  adc srDest
  sta srDest
  clc
  adc srEnd
  dec
  sta srTmp
  dec
  .repeat 13
    lsr
  .endrepeat
  sta srNextMap
  lda srBank
  sec
  sbc #$40
  asl
  asl
  asl
  clc
  adc srNextMap
  sta srNextMap
  cmp srMap
  bne sr_yield
  lda srBatch
  bne sr_ready
sr_yield:
  lda srSaved
  tcs
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  cli
  ; IRQに転送許可を返す機会を作る。CPU描画はPPU DMA中も続行できる。
  nop
  nop
  sei
  lda srNextMap
  sta srMap
  sep #$20
  sta f:$002225
  lda srBank
  pha
  plb
  rep #$20
  lda #8
  sta srBatch
sr_ready:
  ; S=8000も許す。境界のguard上位byteはROMへの書込として捨てる。
  lda srTmp
  dec
  and #$1fff
  clc
  adc #$6001
  tcs
  ldx srDest
sa1_stack_row_begin:
  jml [$00d0]
sr_done:
  lda srSaved
  tcs
  sep #$20
  lda #0
  sta f:$002225
  pha
  plb
  rep #$20
  plp
  sec
  rtl
