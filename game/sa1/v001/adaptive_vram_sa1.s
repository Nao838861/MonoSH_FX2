; 各VRAM面の最終世代以後の変更領域を蓄積する。
; CPUが完了世代を更新したら直近四世代の履歴から再構成する。
; 既に準備したdescriptorが古い世代を含んでも、安全な上位集合になる。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_adaptive_bounds: far, sa1_adaptive_prepare: far
.ifdef SA1_FRONT_DELTA
.export sa1_front_delta_bounds: far, sa1_front_delta_prepare: far
.endif
.segment "BOOT"
avPage=$a0
avGeneration=$a2
avRemaining=$a4
avCursor=$a6
avCount=$a8
avBytes=$aa
avLength=$ac
avStart=$ae
avEnd=$b0
avDest=$b4
avSource=$b8
avOutput=$bc
avRow=$c0
avPending=$c2

sa1_adaptive_bounds:
  rep #$30
  lda $0116
  bne av_capture
  lda #0
  sta f:$4360c0
  sta f:$4360c2
  ldx #0
av_initialize:
  .ifdef SA1_NATIVE_BACKGROUND
  lda #128
  .else
  lda #0
  .endif
  sta f:$436000,x
  sta f:$436060,x
  .ifdef SA1_NATIVE_BACKGROUND
  lda #0
  .else
  lda #128
  .endif
  sta f:$436002,x
  sta f:$436062,x
  inx
  inx
  inx
  inx
  cpx #96
  bcc av_initialize
av_capture:
  lda $0188
  and #3
  jsr av_history_address
  sta avSource
  sep #$20
  lda #$43
  sta avSource+2
  rep #$20
  ldx #0
  ldy #0
av_capture_words:
  lda $0120,x
  sta f:$436400,x
  sta [avSource],y
  inx
  inx
  iny
  iny
  cpx #96
  bcc av_capture_words
  rtl

av_history_address:
  ; A=ring index 0..3、返値=6100+96*index。
  .repeat 5
    asl
  .endrepeat
  sta avCursor
  asl
  clc
  adc avCursor
  adc #$6100
  rts

sa1_adaptive_prepare:
  rep #$30
  stz avPage
av_page:
  lda avPage
  beq :+
  lda #$6060
  bra av_pending_ready
:
  lda #$6000
av_pending_ready:
  sta avDest
  sep #$20
  lda #$43
  sta avDest+2
  sta avSource+2
  rep #$20
  ldx avPage
  sep #$20
  lda $018a,x
  rep #$20
  and #255
  sta avGeneration
  txa
  asl
  tax
  lda avGeneration
  cmp f:$4360c0,x
  jeq av_current_only
  sta f:$4360c0,x
  ldy #0
av_reset_pending:
  lda #128
  sta [avDest],y
  iny
  iny
  lda #0
  sta [avDest],y
  iny
  iny
  cpy #96
  bcc av_reset_pending
  lda $0188
  and #255
  sec
  sbc avGeneration
  and #255
  sta avRemaining
  jeq av_page_done
  cmp #5
  jcs av_full_pending
av_rebuild:
  inc avGeneration
  lda avGeneration
  and #3
  jsr av_history_address
  sta avSource
  jsr av_merge
  dec avRemaining
  bne av_rebuild
  bra av_page_done
av_full_pending:
  ldy #0
av_full_words:
  lda #0
  sta [avDest],y
  iny
  iny
  lda #128
  sta [avDest],y
  iny
  iny
  cpy #96
  bcc av_full_words
  bra av_page_done
av_current_only:
  lda #$6400
  sta avSource
  jsr av_merge
av_page_done:
  inc avPage
  lda avPage
  cmp #2
  jcc av_page
  lda #$6000
  sta avSource
  lda #$0800
  sta avOutput
  jsr av_descriptors
  lda avBytes
  sta $0118
  lda avCount
  sta $011a
  lda #$6060
  sta avSource
  lda #$0a00
  sta avOutput
  jsr av_descriptors
  lda avBytes
  sta $0190
  lda avCount
  sta $0192
  rtl

av_merge:
  ldy #0
av_merge_band:
  lda [avSource],y
  cmp [avDest],y
  bcs :+
  sta [avDest],y
:
  iny
  iny
  lda [avSource],y
  cmp [avDest],y
  bcc :+
  sta [avDest],y
:
  iny
  iny
  cpy #96
  bcc av_merge_band
  rts

av_descriptors:
  sep #$20
  lda #$43
  sta avOutput+2
  rep #$20
  stz avCount
  stz avBytes
  stz avRow
  stz avPending
av_descriptor_band:
  ldy avRow
  lda [avSource],y
  sta avStart
  iny
  iny
  lda [avSource],y
  sec
  sbc avStart
  jmi av_descriptor_next
  jeq av_descriptor_next
  .repeat 3
    asl
  .endrepeat
  sta avLength
  lda avStart
  .repeat 3
    asl
  .endrepeat
  sta avStart
  lda avRow
  xba
  clc
  adc avStart
  sta avStart
  lda avCount
  beq av_new_descriptor
  lda avStart
  sec
  sbc avEnd
  cmp #193
  bcs av_new_descriptor
  clc
  adc avLength
  sta avLength
  clc
  adc avBytes
  sta avBytes
  ldy avPending
  lda [avOutput],y
  clc
  adc avLength
  sta [avOutput],y
  iny
  iny
  lda [avOutput],y
  clc
  dey
  dey
  adc [avOutput],y
  sta avEnd
  bra av_descriptor_next
av_new_descriptor:
  lda avCount
  asl
  sta avPending
  asl
  clc
  adc avPending
  sta avPending
  tay
  lda avLength
  sta [avOutput],y
  clc
  adc avBytes
  sta avBytes
  lda avStart
  clc
  adc avLength
  sta avEnd
  iny
  iny
  lda avStart
  sta [avOutput],y
  lsr
  iny
  iny
  sta [avOutput],y
  inc avCount
av_descriptor_next:
  lda avRow
  clc
  adc #4
  sta avRow
  cmp #96
  jcc av_descriptor_band
  rts

.ifdef SA1_FRONT_DELTA
sa1_front_delta_bounds:
  rep #$30
  ldx #0
front_delta_capture:
  lda $0120,x
  sta f:$436400,x
  inx
  inx
  cpx #96
  bcc front_delta_capture
  rtl
sa1_front_delta_prepare:
  rep #$30
  sep #$20
  lda #$43
  sta avSource+2
  rep #$20
  lda #$6400
  sta avSource
  lda #$0800
  sta avOutput
  jsr av_descriptors
  lda avBytes
  sta $0118
  lda avCount
  sta $011a
  ; 一括更新できない場合だけ、裏面を全面更新する。
  ldx #0
front_delta_full:
  lda #0
  sta f:$436000,x
  lda #128
  sta f:$436002,x
  inx
  inx
  inx
  inx
  cpx #96
  bcc front_delta_full
  lda #$6000
  sta avSource
  lda #$0a00
  sta avOutput
  jsr av_descriptors
  lda avBytes
  sta $0190
  lda avCount
  sta $0192
  rtl
.endif
