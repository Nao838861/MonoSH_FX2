; 非表示期間に収まるCHR記述子の先頭部分を選ぶ。最後のmapは含めない。
.setcpu "65816"
.smart
.macpack longbranch
.ifndef SA1_PREFIX_DESC_COST
SA1_PREFIX_DESC_COST=76
.endif
.import pipe_records, pipe_record_offset, pipe_available, pipe_time_left
.export pipe_prefix_plan: far, pfPartial, pfBytes, pfDesc
.segment "BSS"
pfPartial: .res 2
pfBytes: .res 2
pfDesc: .res 2
pfCost: .res 2
pfLength: .res 2
pfEnd: .res 2
pfAvailable: .res 2
pfTemp: .res 2
.segment "CODE"
.a16
.i16
pipe_prefix_plan:
  rep #$30
  stz pfPartial
  stz pfBytes
  stz pfDesc
  stz pfCost
  lda pipe_available
  sec
  sbc #384
  jmi pf_empty
  sta pfAvailable
  ldx pipe_record_offset
  lda pipe_records+2,x
  sec
  sbc #6
  clc
  adc pipe_record_offset
  adc #208
  sta pfEnd
  lda pipe_records+4,x
  clc
  adc pipe_record_offset
  adc #208
  tax
pf_next:
  cpx pfEnd
  bcs pf_done
  lda pipe_records,x
  sta pfLength
  .repeat 5
    lsr
  .endrepeat
  sta pfTemp
  lsr
  lsr
  clc
  adc pfTemp
  adc pfLength
  adc #SA1_PREFIX_DESC_COST
  adc pfCost
  cmp pfAvailable
  bcs pf_done
  sta pfCost
  lda pfBytes
  clc
  adc pfLength
  sta pfBytes
  lda pfDesc
  clc
  adc #6
  sta pfDesc
  txa
  clc
  adc #6
  tax
  bra pf_next
pf_done:
  lda pfDesc
  beq pf_empty
  phx
  jsr pipe_time_left
  plx
  lda pipe_available
  sec
  sbc #384
  bmi pf_reset
  sta pfAvailable
pf_trim:
  lda pfCost
  cmp pfAvailable
  bcc pf_ready
  lda pfDesc
  beq pf_empty
  txa
  sec
  sbc #6
  tax
  lda pipe_records,x
  sta pfLength
  .repeat 5
    lsr
  .endrepeat
  sta pfTemp
  lsr
  lsr
  clc
  adc pfTemp
  adc pfLength
  adc #SA1_PREFIX_DESC_COST
  sta pfTemp
  lda pfCost
  sec
  sbc pfTemp
  sta pfCost
  lda pfBytes
  sec
  sbc pfLength
  sta pfBytes
  lda pfDesc
  sec
  sbc #6
  sta pfDesc
  bra pf_trim
pf_reset:
  stz pfDesc
  stz pfBytes
pf_ready:
  lda pfDesc
  beq pf_empty
  lda #1
  sta pfPartial
  sec
  rtl
pf_empty:
  clc
  rtl
