from datetime import date

import pytest

from ingest import obour


def card(name, lo, hi, unit='كيلو'):
    # Same markup as oboormarket.org.eg/prices_ar.aspx
    return (f"<div class='card'><span style='x' class='status'>{unit}</span><img src='item_picture/1.jpg' />"
            f"<div class='card-header'><h5 style=' margin:0;'>{name}</h5> </div><div class='card-block'>"
            f"<h6 class='card-title'> من سعر : <strong> {lo}</strong> الى سعر : <strong> {hi}</strong> </h6>"
            f"<p>  العبوة: <strong>جوال </strong></p></div></div>")


FILLER = [card(f'صنف {i}', 1, 2) for i in range(20)]


def page(cards, stamp='10/26/2026'):
    return f"<header><h4> تاريخ اليوم : {stamp}</h4></header>" + ''.join(cards + FILLER)


def test_varieties_combine_and_lookalikes_are_excluded():
    items = obour.parse_items(page([
        card('فلفل رومي بلدى', 8, 10),
        card('فلفـل حامـى صـوب', 6, 11),          # tatweel in the name
        card('فلفل الوان (اصفر-احمر-برتقالى)', 35, 40),
        card('بصل أبيض', 15, 21),
        card('بصل اخضر( الرابطة كيلو)', 20, 30),
        card('برتقال بلدى', 9, 15),
        card('ليمون حلو', 20, 0),                 # max 0 = single price; lemons aren't the citrus series
        card('بلح سيوى', 40, 0),
    ]))
    rows = {r['crop_id']: r for r in obour.to_prices(date(2026, 10, 26), items)}
    assert set(rows) == {'pepper', 'onion', 'citrus', 'date'}
    assert (rows['pepper']['min_egp_per_kg'], rows['pepper']['max_egp_per_kg']) == (6, 11)
    assert rows['pepper']['avg_egp_per_kg'] == 8.75      # mean of 9 and 8.5
    assert rows['onion']['max_egp_per_kg'] == 21
    assert rows['date']['avg_egp_per_kg'] == 40
    assert rows['citrus']['price_date'] == '2026-10-26'


def test_non_kilo_units_are_skipped():
    items = obour.parse_items(page([card('طماطم', 100, 150, unit='قفص')]))
    assert obour.to_prices(date(2026, 10, 26), items) == []


@pytest.mark.parametrize('stamp,today,expected', [
    ('10/26/2026', date(2026, 10, 29), date(2026, 10, 26)),
    ('3/4/2026', date(2026, 3, 5), date(2026, 3, 4)),     # read as M/D, nearest to today
    ('4/3/2026', date(2026, 3, 5), date(2026, 3, 4)),     # D/M only makes sense this way
])
def test_page_date(stamp, today, expected):
    assert obour.page_date(page([], stamp), today) == expected


def test_stale_or_missing_date_and_broken_layout_fail_loudly():
    with pytest.raises(ValueError, match='last 10 days'):
        obour.page_date(page([], '1/1/2025'), date(2026, 10, 29))
    with pytest.raises(ValueError, match='not found'):
        obour.page_date('<html></html>', date(2026, 10, 29))
    with pytest.raises(ValueError, match='layout changed'):
        obour.parse_items(card('طماطم', 1, 2))
