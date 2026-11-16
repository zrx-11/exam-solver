#!/usr/bin/env python3
"""把 统考真题/*.md 合并进 data.js。

每题在 Markdown 里写成 `### N` 开头的一节，节内用 **题目** / **答案** / **考点** /
**思路** / **解答** / **易错点** 作小标题。脚本把每一节转成站点的一条 doc：
全国统考作为「院校」，年份+科目（如 2025 数学一）作为「科目」，题号为序号。

data.js 以现有文件为基准增量合并，不动已有 180 条，可反复运行（会先清掉旧的统考部分）。
"""
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "统考真题")
DATA = os.path.join(ROOT, "data.js")

LABELS = [
    ("题目", "题目"),
    ("答案", "答案"),
    ("考点", "题型识别"),
    ("思路", "解题思路推演"),
    ("解答", "正式解答"),
    ("易错点", "易错点"),
]


def plain(s):
    s = re.sub(r"\$\$[\s\S]*?\$\$", "", s)
    s = re.sub(r"\$[^$]*\$", "", s)
    s = re.sub(r"[*_`#]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_paper(path):
    text = io.open(path, encoding="utf-8").read()
    name = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r"(\d{4})-(数学.+)", name)
    if not m:
        return None
    year, paper = m.group(1), m.group(2)
    parts = re.split(r"(?m)^###\s+(\d{1,2})\s*(?:[（(][^）)]*[）)])?\s*$", text)
    out = []
    for k in range(1, len(parts), 2):
        no, body = int(parts[k]), parts[k + 1]
        body = re.split(r"(?m)^---\s*$", body)[0]
        secs = {}
        pos = [(mm.start(), mm.group(1)) for mm in re.finditer(r"(?m)^\*\*(题目|答案|考点|思路|解答|易错点)\*\*", body)]
        for j, (p, lab) in enumerate(pos):
            end = pos[j + 1][0] if j + 1 < len(pos) else len(body)
            seg = body[p:end]
            seg = re.sub(r"(?m)^\*\*" + lab + r"\*\*[　\s]*", "", seg).strip()
            secs[lab] = seg
        if "题目" not in secs:
            continue
        kind = plain(secs.get("考点", "")).split("；")[0][:26]
        title = "第 %d 题　%s" % (no, kind) if kind else "第 %d 题" % no
        md = []
        for key, head in LABELS:
            if key not in secs or not secs[key]:
                continue
            md.append("## " + head + "\n\n" + secs[key])
        out.append(dict(no=no, title=secs["题目"][:70], titlePlain=title,
                        type=plain(secs.get("考点", ""))[:50], md="\n\n".join(md)))
    return year, paper, out


def main():
    raw = io.open(DATA, encoding="utf-8").read().strip()
    prefix = "window.__EXAM__="
    assert raw.startswith(prefix), "data.js 格式不符"
    data = json.loads(raw[len(prefix):].rstrip(";"))

    # 清掉上一次并入的统考内容（它们总在末尾，删掉不影响已有索引）
    data["docs"] = [d for d in data["docs"] if d.get("school") != "全国统考"]
    data["schools"] = [s for s in data["schools"] if s["name"] != "全国统考"]

    ORDER = {"数学一": 1, "数学二": 2, "数学三": 3, "数学四": 4,
             "数学试卷I": 1, "数学试卷II": 2, "数学试卷III": 3, "数学试卷IV": 4, "数学试卷V": 5,
             "数学农": 6, "数学（农）": 6}
    def sort_key(fn):
        m = re.match(r"(\d{4})-(数学.+?)\.md$", fn)
        return (-int(m.group(1)), ORDER.get(m.group(2), 9))
    files = sorted([p for p in os.listdir(SRC) if re.match(r"\d{4}-数学.+\.md$", p)], key=sort_key)
    subjects = []
    base = len(data["docs"])
    for fn in files:
        res = parse_paper(os.path.join(SRC, fn))
        if not res:
            continue
        year, paper, probs = res
        label = "%s %s" % (year, paper.replace("数学", "数学"))
        label = "%s %s" % (year, {"数学农": "数学（农）"}.get(paper, paper.replace("数学试卷", "试卷")))
        items = []
        for p in probs:
            idx = len(data["docs"])
            data["docs"].append({
                "school": "全国统考",
                "subject": label,
                "subjectLabel": label,
                "no": p["no"],
                "noLabel": "%02d" % p["no"],
                "title": p["title"],
                "titlePlain": p["titlePlain"],
                "type": p["type"],
                "md": p["md"],
            })
            items.append(idx)
        if items:
            subjects.append({"key": label, "label": label, "items": items})

    if subjects:
        school = {"name": "全国统考", "subjects": subjects,
                  "count": sum(len(s["items"]) for s in subjects)}
        data["schools"].append(school)
        data["schools"].sort(key=lambda s: -s["count"])

    data["total"] = len(data["docs"])
    js = prefix + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    io.open(DATA, "w", encoding="utf-8").write(js)
    print("docs %d -> %d, 统考 %d 题" % (base, data["total"], data["total"] - base))


if __name__ == "__main__":
    main()
