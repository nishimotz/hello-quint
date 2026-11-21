# compare-pytest

`docs/compare-pytest.md` の実測に使ったコード。pytest では売り越しバグを捕まえにくいことを示す。

```bash
uv run --with pytest pytest -q test_ticket_service.py   # 3 passed（バグを見逃す）
uv run --with pytest pytest -q test_interleaved.py      # 1 failed
```

`test_interleaved.py` は**わざと失敗する**ので、`test_ticket_service.py` と混ぜて1回で走らせない（混ぜると必ず exit 1 になる）。比較を見たいので別ファイルにしてある。
