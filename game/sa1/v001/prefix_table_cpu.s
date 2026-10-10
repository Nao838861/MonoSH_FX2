; SA-1が作った累積費用表で、転送する記述子数を二分探索する。
.setcpu "65816"
.smart
.macpack longbranch
.import pipe_records, pipe_record_offset, pipe_available, pipe_time_left
.export pipe_prefix_plan: far, pfPartial, pfBytes, pfDesc, sd_collect_costs: far
.segment "COLORBSS"
pfTables: .res 256*8
.segment "BSS"
pfPartial: .res 2
pfBytes: .res 2
pfDesc: .res 2
pfBase: .res 2
pfBeforeBytes: .res 2
pfBeforeCost: .res 2
pfStart: .res 2
pfLow: .res 2
pfHigh: .res 2
pfMid: .res 2
pfLimit: .res 2
.segment "GSU"
.a16
.i16
sd_collect_costs:
  php
  phx
  phy
  rep #$30
  lda f:$00311a
  dec
  beq pf_collect_done
  asl
  asl
  sta f:$004305
  lda pipe_records,x
  and #$8400
  clc
  adc #$6600
  sta f:$004302
  txa
  lsr
  clc
  adc #pfTables
  sta f:$002181
  sep #$20
  lda #0
  sta f:$002183
  lda pipe_records,x
  sta f:$004304
  lda #$95
  sta f:$002231
  lda #1
  sta f:$00420b
pf_collect_done:
  rep #$30
  ply
  plx
  plp
  rtl
.segment "CODE"
.a16
.i16
pipe_prefix_plan:
  rep #$30
  stz pfPartial
  stz pfBytes
  stz pfDesc
  ldx pipe_record_offset
  txa
  lsr
  clc
  adc #pfTables
  sta pfBase
  lda pipe_records+4,x
  sta f:$004204
  sep #$20
  lda #6
  sta f:$004206
  rep #$20
  .repeat 8
    nop
  .endrepeat
  lda f:$004214
  sta pfStart
  sta pfLow
  lda pipe_records+2,x
  sta f:$004204
  sep #$20
  lda #6
  sta f:$004206
  rep #$20
  .repeat 8
    nop
  .endrepeat
  lda f:$004214
  dec
  sta pfHigh
  stz pfBeforeBytes
  stz pfBeforeCost
  lda pfStart
  beq pf_budget
  dec
  asl
  asl
  clc
  adc pfBase
  tax
  lda a:0,x
  sta pfBeforeBytes
  lda a:2,x
  sta pfBeforeCost
pf_budget:
  jsr pipe_time_left
  lda pipe_available
  sec
  sbc #384
  jmi pf_empty
  clc
  adc pfBeforeCost
  sta pfLimit
pf_search:
  lda pfLow
  cmp pfHigh
  bcs pf_found
  clc
  adc pfHigh
  inc
  lsr
  sta pfMid
  dec
  asl
  asl
  clc
  adc pfBase
  tax
  lda a:2,x
  cmp pfLimit
  bcs pf_lower
  lda pfMid
  sta pfLow
  bra pf_search
pf_lower:
  lda pfMid
  dec
  sta pfHigh
  bra pf_search
pf_found:
  lda pfLow
  sec
  sbc pfStart
  beq pf_empty
  asl
  sta pfDesc
  asl
  clc
  adc pfDesc
  sta pfDesc
  lda pfLow
  dec
  asl
  asl
  clc
  adc pfBase
  tax
  lda a:0,x
  sec
  sbc pfBeforeBytes
  sta pfBytes
  lda #1
  sta pfPartial
  sec
  rtl
pf_empty:
  clc
  rtl
