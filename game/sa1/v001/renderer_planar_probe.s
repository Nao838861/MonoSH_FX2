; 固定fixtureで直接planar描画の上限を測る。ゲーム用の位置・縮小検索は含まない。
.setcpu "65816"
.smart
.import planar_probe_programs: far
.export sa1_entry,sa1_clear_start,sa1_clear_done,sa1_draw_start,sa1_draw_done
.segment "SA1"
sa1_entry:
  sei
  clc
  xce
  rep #$30
  lda #$01ff
  tcs
  lda #0
  tcd
  sep #$20
  pha
  plb
  lda #$80
  sta $2227
  lda #$22
  sta $07f0
  lda #$6b
  sta $07f4
wait_job:
  rep #$30
  lda $0100
  beq wait_job
sa1_clear_start:
  sep #$20
  lda #$84
  sta $2230
  stz $2232
  lda #$80
  sta $2233
  lda #2
  sta $2234
  stz $2235
  stz $2236
  rep #$20
  lda #$6000
  sta $2238
  sep #$20
  lda #$40
  sta $2237
  rep #$30
sa1_clear_done:
  lda $0108
  sta $20
  asl
  clc
  adc $20
  tax
  lda f:planar_probe_programs,x
  sta $07f1
  sep #$20
  lda f:planar_probe_programs+2,x
  sta $07f3
  lda #$40
  pha
  plb
  rep #$20
sa1_draw_start:
  jsl $0007f0
  sep #$20
  lda #0
  pha
  plb
  rep #$20
sa1_draw_done:
  lda #1
  sta $0104
wait_release:
  lda $0100
  bne wait_release
  stz $0104
  jmp wait_job
.assert * <= $07d0,error,"planar probe exceeds IRAM"
