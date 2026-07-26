def count_word_frequency(text):
    """统计文本词频，返回TOP20"""
    if not text or not isinstance(text, str):
        return {}
    words = text.split()
    freq = {}
    for w in words:
        w = w.strip(".,!?;:'\"()").lower()
        freq[w] = freq.get(w, 0) + 1
    return dict(sorted(freq.items(), key=lambda x: -x[1])[:20])
