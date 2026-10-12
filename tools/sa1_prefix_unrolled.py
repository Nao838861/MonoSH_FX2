"""最大48記述子の累積費用探索を、6段の固定探索へ展開する。"""


def source(text):
    begin=text.index('pf_search:\n');end=text.index('pf_found:\n',begin)
    result=['pf_search:','  phy','  lda pfHigh','  asl','  asl','  clc','  adc pfBase',
        '  sec','  sbc #4','  sta pfMid','  lda pfBase','  sec','  sbc #4','  tay']
    for bit in (32,16,8,4,2,1):
        name='pf_lift_'+str(bit)
        result += ['  tya','  clc','  adc #'+str(bit*4),'  cmp pfMid',
            '  bcc '+name+'_within','  bne '+name+'_skip',name+'_within:',
            '  tax','  lda a:2,x','  cmp pfLimit','  bcs '+name+'_skip','  txy',name+'_skip:']
    result += ['  tya','  sec','  sbc pfBase','  clc','  adc #4','  lsr','  lsr','  sta pfLow','  ply']
    exports='.export pf_search, pf_found, pfBase, pfHigh, pfLow, pfMid, pfLimit\n'
    return exports+text[:begin]+'\n'.join(result)+'\n'+text[end:]


def one_pass_pipeline(text):
    """累積表の一回の予算計算で、一括・途中転送をどちらも選ぶ。"""
    begin=text.index('  lda pipe_records+2,x\n',text.index('pipe_try_fast_dma:\n'))
    end=text.index('pf_frame_bytes:\n',begin)
    text=text[:begin]+'''  lda pipe_records+4,x
  cmp pipe_records+2,x
  jeq pipe_fast_empty
  jsl $c10000+pipe_prefix_plan
  jcc pipe_fast_unavailable
  ldx pipe_record_offset
  lda pfBytes
'''+text[end:]
    return text


def one_pass_source(text,full_reserve=384):
    assert full_reserve in (192,384)
    old='  sta pfLimit\npf_search:\n'
    assert text.count(old)==1
    check='''  sta pfLimit
pf_full_check:
  ; 全量が収まる場合は、6段探索も省く。
  lda pfHigh
  dec
  asl
  asl
  clc
  adc pfBase
  tax
  lda a:2,x
  cmp pfLimit
  bcs pf_search
  lda pfHigh
  sta pfLow
  jmp pf_found
pf_search:
'''
    if full_reserve==192:
        check=check.replace('pf_full_check:\n','pf_full_check:\n  lda pfLimit\n  clc\n  adc #192\n  sta pfMid\n')
        check=check.replace('  cmp pfLimit\n','  cmp pfMid\n')
    text='.export pf_full_check\n'+text.replace(old,check,1)
    old='  lda #1\n  sta pfPartial\n  sec\n  rtl\n'
    assert text.count(old)==1
    return text.replace(old,'''  lda pfLow
  cmp pfHigh
  beq pf_all_selected
  lda #1
  sta pfPartial
pf_all_selected:
  sec
  rtl
''',1)
