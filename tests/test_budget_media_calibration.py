"""媒体作业的峰值由作业参数估算，不由运行时的整机内存差额标定。

这个文件原先有四条测试，测的是「作业跑完用 available_bytes 的基线减最低点记下
本机实测峰值」那套机制。那套机制已删除，因为它的方向是危险的那一边：

后来量到 `available_bytes`（free+inactive+purgeable+speculative）对常驻内存
只捕捉 51–73%——mmap 的模型权重 51%、匿名页 73%。用「基线 − 最低点」记下的
峰值因此系统性偏低，而 `measured` 优先于 `predicted`，于是预算会以为视频只要
14 GiB（实际 27），放行装不下的组合。

而且它本来就不必要：作业峰值是**作业本身的属性**（模型 + 分辨率 × 帧数），
不是机器的属性——同样的参数在任何机器上要的内存都一样。
"""
import inspect

from desk.media import service as media_service
from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3


def test_media_peak_is_not_calibrated_from_the_available_memory_delta():
    """守住上面那条规则：别再把整机差额当成峰值的标定来源。"""
    source = inspect.getsource(media_service)
    for gone in ("_record_media_peak", "_sample_available", "record_media("):
        assert gone not in source, \
            f"{gone} 又回来了——整机差额系统性偏低，用它标定峰值方向朝 OOM"


def test_the_estimate_still_follows_the_job_parameters():
    """按参数估算这条必须留着：不同分辨率/帧数的作业要的内存不同。

    R-budget-06 当初就是因为「报模型的磁盘体积、每个作业都是同一个数」而改成
    按参数算的；别在删掉标定时把这条一起删了。
    """
    draft = estimate_bytes("video", {"width": 512, "height": 288, "frames": 49, "steps": 16})
    sharp = estimate_bytes("video", {"width": 1024, "height": 576, "frames": 73, "steps": 16})
    assert sharp > draft, "分辨率与帧数翻倍，估算值没跟着涨"
    assert 25 * GIB <= draft <= 31 * GIB, "草稿档偏离了 2026-09-08 的实测标定"


def test_music_has_its_own_shape():
    ten = estimate_bytes("music", {"duration": 10})
    sixty = estimate_bytes("music", {"duration": 60})
    assert sixty > ten
