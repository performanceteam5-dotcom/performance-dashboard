import pandas as pd
from comment_generator import format_won, format_cpu, build_mutandard_comment


def test_format_won_man():
    assert format_won(16_900_000) == '1,690만원'

def test_format_won_eok():
    assert format_won(100_000_000) == '1억원'

def test_format_won_mixed():
    assert format_won(176_170_000) == '1억 7,617만원'

def test_format_cpu():
    assert format_cpu(112) == '112원'
    assert format_cpu(None) == '—'


def _make_part_df():
    rows = [
        {'일': '2026-05-14', '캠페인/구분': '무탠다드맨', '상세구분': '기획전',
         '광고비_Fee포함': 2_000_000, 'GA_활성사용자수': 20000,
         'GA_고활성사용자수': 16000, 'GA_저활성사용자수': 4000, '매체_표기': '메타'},
        {'일': '2026-05-14', '캠페인/구분': '무탠다드맨', '상세구분': '상시',
         '광고비_Fee포함': 1_000_000, 'GA_활성사용자수': 10000,
         'GA_고활성사용자수': 8000, 'GA_저활성사용자수': 2000, '매체_표기': '카카오'},
        {'일': '2026-05-14', '캠페인/구분': '무탠다드맨', '상세구분': '캠페인',
         '광고비_Fee포함': 3_000_000, 'GA_활성사용자수': 10000,
         'GA_고활성사용자수': 8000, 'GA_저활성사용자수': 2000, '매체_표기': '메타'},
        {'일': '2026-05-14', '캠페인/구분': '무탠다드통합', '상세구분': '카탈로그',
         '광고비_Fee포함': 6_000_000, 'GA_활성사용자수': 54000,
         'GA_고활성사용자수': 43000, 'GA_저활성사용자수': 11000, '매체_표기': '카카오'},
    ]
    df = pd.DataFrame(rows)
    df['일'] = pd.to_datetime(df['일'])
    return df


def test_build_mutandard_comment_contains_header():
    df = _make_part_df()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), df.copy())
    assert '#무탠유입' in comment

def test_build_mutandard_comment_segment_headers():
    df = _make_part_df()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), df.copy())
    assert '[무탠다드맨]' in comment
    assert '[무탠다드통합]' in comment

def test_build_mutandard_comment_detail_headers():
    df = _make_part_df()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), df.copy())
    assert '기획전+상시' in comment
    assert '캠페인' in comment
    assert '카탈로그' in comment

def test_build_mutandard_comment_no_split_for_integrated():
    """무탠다드통합은 '기획전+상시' 항목이 코멘트에 없어야 한다."""
    df = _make_part_df()
    comment = build_mutandard_comment(df, pd.Timestamp('2026-05-14'), df.copy())
    integrated_pos = comment.index('[무탠다드통합]')
    after_integrated = comment[integrated_pos:]
    assert '기획전+상시' not in after_integrated
