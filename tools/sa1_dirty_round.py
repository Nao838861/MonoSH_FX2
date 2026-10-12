"""tile帯indexへのfloor変換を、同じA/C/N/Zになる2命令へ短縮する。"""


def transform(name,text):
    old='  .repeat 3\n    lsr\n  .endrepeat\n  asl\n  asl\n'
    assert name in ('dirty','row_dirty')
    assert text.count(old)==(4 if name=='dirty' else 2)
    # 16bit Aの全値について ((A >> 3) << 2) == ((A & FFF8) >> 1)。
    # 最後のASL/LSRのcarryはいずれも0、N/Zも同じ。Vはどちらも不変。
    assert all(((a>>3)<<2)==((a&0xfff8)>>1) for a in range(65536))
    return text.replace(old,'  and #$fff8\n  lsr\n')
