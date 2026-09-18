from __future__ import annotations

"""Small high-signal 2026 China layer for the portfolio catalog.

These records are not meant to replace a licensed entertainment feed. They solve a demo problem:
public metadata sources can lag current Chinese releases, so we keep a transparent curated layer
with official/public source URLs and let the normal poster fallback policy fill missing artwork.
"""

def curated_2026_records(record_cls):
    Record = record_cls
    film_bureau_spring = "https://www.chinafilm.gov.cn/xwzx/gzdt/202602/t20260209_949645.html"
    film_bureau_summer = "https://www.chinafilm.gov.cn/xwzx/ywxx/202606/t20260625_996069.html"

    rows = [
        Record(
            content_id="curated-cn26-jingzhe-wusheng", title="惊蛰无声", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Thriller","Crime","Action"],
            overview="国安小组围绕重要情报外泄展开调查，随着调查深入，一场无声较量逐渐展开。",
            poster_url="https://media.bjnews.com.cn/image/2026/01/22/5678358836604382139.jpg",
            source="china_film_bureau_curated", source_url=film_bureau_spring,
        ),
        Record(
            content_id="curated-cn26-biaoren", title="镖人：风起大漠", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Action","Adventure","Drama"],
            overview="大漠镖客受托护送神秘人物前往长安，途中遭遇围剿，宿命羁绊逐渐揭开。",
            poster_url="https://k.sinaimg.cn/n/sinakd20260226s/320/w800h1120/20260226/228c-27c3ae5d1587e27d133e8ecf0498ef24.jpg/w700d1q75cms.jpg",
            source="china_film_bureau_curated", source_url=film_bureau_spring,
        ),
        Record(
            content_id="curated-cn26-feichi3", title="飞驰人生3", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Comedy","Drama","Sport"],
            overview="最后一届巴音布鲁克拉力赛落幕后，赛车手回归现实，面对新的挑战与生活。",
            poster_url="https://wx4.sinaimg.cn/middle/007cUgzRly1i9kks3gzxej31jk2cle82.jpg",
            source="china_film_bureau_curated", source_url=film_bureau_spring,
        ),
        Record(
            content_id="curated-cn26-xinghe-rumeng", title="星河入梦", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Science-Fiction","Adventure","Comedy"],
            overview="近未来虚拟梦境系统“良梦”问世后，管理员与舰长穿梦闯关，展开梦境冒险。",
            poster_url="https://imgcache.dealmoon.com/thumbimg.dealmoon.com/us2603/dealmoon/4cf/abc/6f0/2c206a410fdbbe0235a9f1cx1440x2300x1414.jpeg_1080_0_3_462d.jpeg",
            source="china_film_bureau_curated", source_url=film_bureau_spring,
        ),
        Record(
            content_id="curated-cn26-panda", title="熊猫计划之部落奇遇记", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Comedy","Adventure","Family"],
            overview="熊猫胡胡与国际巨星意外置身神奇部落，并帮助部落解决接连出现的难题。",
            poster_url="https://p9.qhimg.com/t11508c75c81ba0e41daa77c045.jpg",
            source="china_film_bureau_curated", source_url=film_bureau_spring,
        ),
        Record(
            content_id="curated-cn26-boonie", title="熊出没·年年有熊", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Animation","Comedy","Family","Adventure"],
            overview="不速之客引发危机后，熊大、熊二和光头强再次合作化解问题。",
            poster_url="https://www.yuleonstar.com/media/uploads/2026/02/02/lowddu.jpg",
            source="china_film_bureau_curated", source_url=film_bureau_spring,
        ),
        Record(
            content_id="curated-cn26-qunxing", title="群星闪耀时", content_type="movie",
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Science-Fiction","Adventure","Drama"],
            overview="航天员在太空突遇险情，并收到来自过去的神秘电子信号，需要破译信号援救未来。",
            poster_url="https://x0.ifengimg.com/ucms/2026_16/2880742387955756C1F6AF7F1B2691B3D244D23A_size315_w1080_h1080.jpg",
            source="china_film_bureau_curated", source_url=film_bureau_summer,
        ),
        Record(
            content_id="curated-cn26-jiaye", title="家业", content_type="series",
            origin_platforms=["iqiyi"],
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Drama","History","Romance"],
            overview="徽州贡墨案后，李祯以制墨天赋重振家业，并与骆文谦从竞争走向合作。",
            poster_url="https://s.yimg.com/ny/api/res/1.2/fX2hmMSrGOINdRfCcdYYGA--/YXBwaWQ9aGlnaGxhbmRlcjt3PTk2MDtoPTEyMDA-/https%3A/media.zenfs.com/zh-tw/ebc_star_440/2a033ee36abf8a3241b4d497b8f780ae",
            source="iqiyi_curated", source_url="https://www.iqiyi.com/a_131ig5wtqg5.html",
        ),
        Record(
            content_id="curated-cn26-yiouchun", title="一瓯春", content_type="series",
            origin_platforms=["iqiyi"],
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Drama","Romance","History"],
            overview="谢清圆与沈润在高门与朝堂暗流中互相试探、携手复仇，最终走向新生。",
            poster_url="https://pbs.twimg.com/media/HDmzGWzbAAA5WVS.jpg",
            source="iqiyi_curated", source_url="https://www.iqiyi.com/a_2b9ocx2qugh.html",
        ),
        Record(
            content_id="curated-cn26-shenyuan", title="深渊无间", content_type="series",
            origin_platforms=["iqiyi"],
            release_year=2026, countries=["中国大陆"], language="Chinese",
            genres=["Thriller","Mystery","Crime"],
            overview="推理网文与多年悬案细节高度重合，新警李成在多方嫌疑人之间展开高智对弈。",
            poster_url="https://www.palmyule.com/uploads/20251203/234b85986b1e644d7b7aa81ed2ad6df5.jpg",
            source="iqiyi_curated", source_url="https://www.iqiyi.com/a_okv7zmsbr1.html",
        ),
    ]
    return rows
