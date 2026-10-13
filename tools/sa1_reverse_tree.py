"""木4の逆順native行と、共通hint番号による右端描画。"""
import json
from sa1_prescaled import address

TABLE=0x5f6fe0


def finish(rom,dest):
    packing=json.loads((dest/'compiled_game_packing.json').read_text());hints=[bytes.fromhex(h)for h in packing['treeHints']]
    data=bytearray(len(hints)*3)
    for i,hint in enumerate(hints):
        pointer=address(TABLE+len(data));data[i*3:i*3+3]=pointer.to_bytes(3,'little');data+=hint
    assert TABLE+len(data)<=0x5f8000
    assert not any(rom[TABLE:TABLE+len(data)]),'tree hints overlap occupied ROM'
    rom[TABLE:TABLE+len(data)]=data
    (dest/'reverse_tree_packing.json').write_text(json.dumps(dict(hintCount=len(hints),hintBytes=sum(map(len,hints)),tableBytes=len(hints)*3,
        begin=TABLE,end=TABLE+len(data),originalNativeRowsReplaced=True),indent=2)+'\n')


def fast(text,bypass=False,left=False,left_bypass=False,left_min_bytes=0,dense=False):
    if dense:
        old='  jsl sa1_edge_prepare\n';assert text.count(old)==1
        return '.setcpu "65816"\n.import sa1_dense_stack_tree: far\n'+text.replace(old,old+'''  lda $3e
  cmp #4
  bne dense_tree_other
  jsl sa1_dense_stack_tree
  sec
  rtl
dense_tree_other:
''',1)
    text='.setcpu "65816"\n.import sa1_reverse_tree_right: far\n'+text
    old='  jsl sa1_edge_prepare\n';assert text.count(old)==1
    gate='''  lda $3e
  cmp #4
  bne tree_other
  lda $c4
  beq tree_full
  lda $38
  bmi tree_full
  jsl sa1_reverse_tree_right
  sec
  rtl
tree_full:
  jmp fast_base_ready
tree_other:
'''
    if bypass:
        gate=gate.replace('  jsl sa1_reverse_tree_right\n  sec\n  rtl\n',
            '  jmp tree_full\n  nop\n  nop\n  nop\n',1)
    if left:
        text='.setcpu "65816"\n.import sa1_reverse_tree_left: far\n'+text
        gate=gate.replace('  bmi tree_full\n','''  bpl tree_right_side
  jsl sa1_reverse_tree_left
  sec
  rtl
tree_right_side:
''',1)
        if left_min_bytes:
            gate=gate.replace('  jsl sa1_reverse_tree_left\n',f'  lda $c4\n  cmp #{left_min_bytes}\n  bcc tree_full\n  jsl sa1_reverse_tree_left\n',1)
        if left_bypass:
            gate=gate.replace('  jsl sa1_reverse_tree_left\n  sec\n  rtl\n',
                '  jmp tree_full\n  nop\n  nop\n  nop\n',1)
    return text.replace(old,old+gate,1)
