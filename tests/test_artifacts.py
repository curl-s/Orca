from __future__ import annotations

import pytest

from orbis_diff.artifacts import atomic_place, binary_fingerprint, new_run_dir, sha256_prefix


def test_sha256_prefix_is_deterministic(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello world")
    assert sha256_prefix(f) == sha256_prefix(f)
    assert len(sha256_prefix(f)) == 12


def test_sha256_prefix_differs_for_different_content(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"content A")
    b.write_bytes(b"content B")
    assert sha256_prefix(a) != sha256_prefix(b)


def test_binary_fingerprint_same_name_different_content_differs(tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    a = d1 / "module.elf"
    b = d2 / "module.elf"
    a.write_bytes(b"version 1")
    b.write_bytes(b"version 2 - different")
    assert binary_fingerprint(a) != binary_fingerprint(b)


def test_binary_fingerprint_keeps_readable_stem(tmp_path):
    f = tmp_path / "libSceFoo.sprx"
    f.write_bytes(b"data")
    fp = binary_fingerprint(f)
    assert fp.startswith("libSceFoo_")


def test_new_run_dir_is_fresh_and_unique(tmp_path):
    r1 = new_run_dir(tmp_path)
    r2 = new_run_dir(tmp_path)
    assert r1.exists()
    assert r2.exists()
    assert r1 != r2


def test_atomic_place_moves_file_and_creates_parents(tmp_path):
    src = tmp_path / "scratch" / "out.BinExport"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"payload")

    dst = tmp_path / "stable" / "nested" / "out.BinExport"
    result = atomic_place(src, dst)

    assert result == dst
    assert dst.read_bytes() == b"payload"
    assert not src.exists()


def test_atomic_place_missing_source_raises(tmp_path):
    src = tmp_path / "does_not_exist.BinExport"
    dst = tmp_path / "out.BinExport"
    with pytest.raises(OSError):
        atomic_place(src, dst)
