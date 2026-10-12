"""転送期限の計測labelと、残り時間を求めるROM表を生成する。"""

LABELS=('pipe_choose_target','pipe_setup_transfer','pipe_descriptor','pipe_full_descriptor',
    'pipe_set_chunk','pipe_transfer_pause','pipe_transfer_complete','pipe_reserved',
    'pipe_actual_blank','pipe_fast_group','pipe_fast_groups_done','p3Complete','p3Flip',
    'pipe_no_time','pipe_fast_empty','pipe_fast_unavailable')


def trace(text):
    for name in LABELS:
        # p3 helperは末尾のinclude内にある。
        assert name in ('p3Complete','p3Flip') or text.count(name+':\n')==1,name
    return '.export '+', '.join(LABELS)+'\n'+text


def budget_table(text,deadline):
    begin=text.index('  lda #'+str(deadline)+'\n',text.index('dense_budget_line_ready:\n'))
    end=text.index('  lda pipe_hpoint\n',begin)
    assert text[begin:end].endswith('  sta pipe_available\n')
    code='''  phx
  asl
  tax
  lda f:pipe_budget_lines,x
  sta pipe_available
  plx
  lda pipe_available
  bmi pipe_no_time
'''
    text=text[:begin]+code+text[end:]
    text+='\n.segment "GSU"\n.export pipe_budget_lines: far\npipe_budget_lines:\n'
    text+=''.join('  .word '+str((deadline-i)*170 if i<=deadline else 65535)+'\n' for i in range(512))
    text+='.segment "CODE"\n'
    return text
