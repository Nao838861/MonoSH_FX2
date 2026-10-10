"""dirty矩形の計算中だけコードとtile maskをI-RAMへ置く。"""


def transform(name, text):
    if name == 'row_dirty':
        text = text.replace('.segment "BOOT"', '.segment "DIRTYJIT"')
        text = text.replace('sa1_tile_masks+2,x', 'a:$0602,x').replace('sa1_tile_masks,x', 'a:$0600,x')
    if name in ('dirty', 'row_dirty'):
        text = text.replace('f:$432800,x', 'a:$0700,x').replace('f:$432802,x', 'a:$0702,x')
    if name == 'dirty':
        text = '.setcpu "65816"\n.import sa1_dirty_iram_load: far\n' + text
        text = text.replace('sa1_plan_dirty:\n', 'sa1_plan_dirty:\n  jsl sa1_dirty_iram_load\n', 1)
        old = 'dirty_first:\n  jsl sa1_transfer_mask_capture'
        new = '''dirty_first:
  ldx #0
dirty_mask_copy:
  lda a:$0700,x
  sta f:$432800,x
  inx
  inx
  cpx #96
  bcc dirty_mask_copy
  jsl sa1_transfer_mask_capture'''
        assert old in text
        text = text.replace(old, new, 1)
    return text
