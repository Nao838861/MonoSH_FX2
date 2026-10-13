"""固定予約の一部を、実転送byte数に比例するrefresh費用へ移す。"""
from sa1_fixed_map import change


def direct(text):
    return change(text,'''  sta $be
  lsr
  lsr
  clc
  adc $be
''','''  sta $be
  ; lengthは32byte単位。3*(length/32)=length/32+length/16。
  asl
  clc
  adc $be
  sta $be
  lda $bc
  .repeat 7
    lsr
  .endrepeat
  clc
  adc $be
''')


def partial(text):
    return change(text,'''  sta pfLimit
  lsr
  lsr
  clc
  adc pfLimit
''','''  sta pfLimit
  asl
  clc
  adc pfLimit
  sta pfLimit
  lda pfMid
  .repeat 7
    lsr
  .endrepeat
  clc
  adc pfLimit
''')
