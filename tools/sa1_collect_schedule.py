"""転送候補がある間は、次世代のmetadata収集をIRQの転送経路から外す。"""
from sa1_fixed_map import change


def pipeline(text):
    old='''  .ifndef SA1_STAGED
  jsr pipe_collect
  .endif
  .ifdef SA1_PREFILL
'''
    new='''  .ifndef SA1_STAGED
  ; 途中転送中か、次のread slotがreadyなら、その画像を先に送る。
  ; 完了した次世代はack前で停止しており、main側のcollectまで保持される。
  lda pipe_target_slot
  cmp #$ffff
  bne pipe_collect_skipped
  lda pipe_read_slot
  asl
  tax
  lda pipe_status,x
  cmp #2
  beq pipe_collect_skipped
pipe_collect_urgent:
  jsr pipe_collect
  bra pipe_collect_scheduled
pipe_collect_skipped:
  nop
pipe_collect_scheduled:
  .endif
  .ifdef SA1_PREFILL
'''
    text=change(text,old,new)
    exports='''.export pipe_collect_skipped, pipe_collect_urgent, pipe_collect_publish, pipe_read_slot
.export pipe_collect_main: far, pipe_collect_main_publish: far
pipe_collect_main=$7f0000+pipe_collect
pipe_collect_main_publish=$7f0000+pipe_collect_publish
'''
    return exports+text
