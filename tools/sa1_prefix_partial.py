"""累積費用表から、先頭の記述子を分割転送済みの量を差し引く。"""


def source(text):
    old='pf_budget:\n  jsr pipe_time_left\n'
    assert text.count(old)==1
    return text.replace(old,'''pf_budget:
  ; cumulative[start] - cumulative[start-1] gives the original length.
  lda pfStart
  asl
  asl
  clc
  adc pfBase
  tax
  lda a:0,x
  sec
  sbc pfBeforeBytes
  pha
  ldx pipe_record_offset
  lda pipe_records+4,x
  clc
  adc pipe_record_offset
  adc #208
  tax
  pla
  sec
  sbc pipe_records,x
  jcc pf_empty
  beq pf_partial_accounted
  sta pfMid
  clc
  adc pfBeforeBytes
  sta pfBeforeBytes
  lda pfMid
  .repeat 5
    lsr
  .endrepeat
  sta pfLimit
  lsr
  lsr
  clc
  adc pfLimit
  adc pfMid
  adc pfBeforeCost
  sta pfBeforeCost
pf_partial_accounted:
  jsr pipe_time_left
''',1)
