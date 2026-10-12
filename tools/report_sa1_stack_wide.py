"""幅91追加・右端限定・内部RAM実行の比較を固定する。"""
import shutil
import report_sa1_stack_explosions as report


def main():
    report.DEST=report.ROOT/'game/sa1/v001/results/20261013_stack_wide'
    report.CASES=(
        ('fifostackexpwide_v1','movestress_detinput_captureburst_stackexpwide_v1_tracepalette'),
        ('fifostackexpwide_v2','movestress_detinput_captureburst_stackexpwide_v2_tracepalette'),
        ('fifostackexpiram_v1','movestress_detinput_captureburst_stackexpiram_v1_tracepalette'),
        (None,'stackfixturewide_stackexp_v2_tracepalette'),
        (None,'stackfixturewide_stackiram_v1_tracepalette'),
    )
    d=report.BUILD/'stackfixturewide_stackexp_v2_tracepalette'
    for source,target in (
        ('stackfixturewide_stackexp_v2_test.log','host_verifier_first_run.log'),
        ('verify_saved_wide.log','host_verifier_rerun.log'),
        ('verify_saved_wide.py','verify_saved_wide.py'),
    ):
        shutil.copy2(report.BUILD/source,d/target)
    report.main()


if __name__=='__main__':main()
