"""画面を切り替えないprefix転送だけ、切替予約の時間を転送へ戻す。"""
from sa1_fixed_map import change


def pipeline(text):
    text=change(text,'pipe_time_left:\n  sep #$20\n',
        'pipe_time_left:\n  stz pipe_unreserved\n  sep #$20\n')
    text=change(text,'  adc #128\n  sta pipe_available\n',
        '  adc #128\n  sta pipe_available\n  sta pipe_unreserved\n')
    return '.export pipe_unreserved\n.segment "BSS"\npipe_unreserved: .res 2\n.segment "CODE"\n'+text


def prefix(text,reserve):
    assert 900<=reserve<=1600
    text=change(text,'  stz pfPartial\n','  stz pfPartial\n  stz pfHoldLast\n')
    text=change(text,'  sbc #384\n  jmi pf_empty\n  clc\n',
        '  sbc #384\n  jmi pf_partial_budget\n  clc\n')
    text=change(text,'  bcs pf_search\n  lda pfHigh\n',
        '  bcs pf_partial_budget\n  lda pfHigh\n')
    text=change(text,'pf_search:\n',
        'pf_partial_budget:\n  jsl pf_partial_limit\n  jcc pf_empty\n  sta pfLimit\npf_search:\n')
    text=change(text,'pf_found:\n',
        'pf_found:\n  lda pfHoldLast\n  beq :+\n  inc pfHigh\n:\n')
    text+='''
.segment "BSS"
.export pfHoldLast, pfBeforeCost
pfHoldLast: .res 2
.segment "GSU"
.import pipe_unreserved
.export pf_partial_budget, pf_partial_limit: far
pf_partial_limit:
  ; 全量判定は従来の切替予約のまま。失敗した場合だけここへ来る。
  ; 最後の記述子を必ず残し、増やした予算で完了／画面切替へ進ませない。
  lda pipe_unreserved
  sec
  sbc #'''+str(reserve+384)+'''
  bmi pf_partial_limit_empty
  clc
  adc pfBeforeCost
  pha
  dec pfHigh
  lda #1
  sta pfHoldLast
  pla
  sec
  rtl
pf_partial_limit_empty:
  clc
  rtl
.segment "CODE"
'''
    return text
