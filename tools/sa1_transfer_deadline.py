"""転送期限の計測labelと、残り時間を求めるROM表を生成する。"""

LABELS=('pipe_choose_target','pipe_setup_transfer','pipe_descriptor','pipe_full_descriptor',
    'pipe_set_chunk','pipe_transfer_pause','pipe_transfer_complete','pipe_reserved',
    'pipe_actual_blank','pipe_fast_group','pipe_fast_groups_done','p3Complete','p3Flip',
    'pipe_no_time','pipe_fast_empty','pipe_fast_unavailable','pipe_fast_unroll_start','pipe_fast_unroll_end')


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


def early_flip_prepare(text):
    """次画面のWRAM状態を先に用意し、PPU操作の直前に非表示を待つ。"""
    old='pipe_flip:\n  .ifdef SA1_EARLY_REQUEST\n  jsr pipe_start_blank\n  .endif\n'
    assert text.count(old)==1
    text=text.replace(old,'pipe_flip:\n',1)
    old='  sta pipe_obj_pointer\n  jsr update_ground_pointers\n'
    assert text.count(old)==1
    text=text.replace(old,'''  sta pipe_obj_pointer
pipe_flip_prepared:
  jsr pipe_start_blank
pipe_flip_ppu:
  jsr update_ground_pointers
''',1)
    return '.export pipe_flip_prepared, pipe_flip_ppu\n'+text


def tail_flip_reserve(text,reserve):
    """自機CHR更新なし・残り1024B以下だけ、切替予約を小さくする。"""
    assert reserve==1400
    old='pipe_reserve_small:\n  plx\n  lda pipe_available\n'
    new='''pipe_reserve_small:
  ; 大口DMAの見積り誤差を吸収する2200は維持する。
  lda pipe_records+34,x
  cmp #1025
  bcs pipe_reserve_full_tail
  plx
  lda pipe_available
  sec
  sbc #1400
  bra pipe_reserved
pipe_reserve_full_tail:
  plx
  lda pipe_available
'''
    assert text.count(old)==1
    return text.replace(old,new,1)


def request_line(text,line):
    """IRQと準備待ちだけを早める。PPUの非表示開始203／表示開始22は維持する。"""
    from sa1_fixed_map import change
    assert 180<=line<197
    text=change(text,'  lda #197\n  .else\n  lda #203\n',
        f'  lda #{line}\n  .else\n  lda #203\n')
    text=change(text,'  cmp #197\n  bcs pipe_wait_actual_blank\n',
        f'  cmp #{line}\n  bcs pipe_wait_actual_blank\n')
    text=change(text,'  cmp #197\n  bcc dense_budget_next_field\n',
        f'  cmp #{line}\n  bcc dense_budget_next_field\n')
    return text
