from core.dashboard_totals import total_recoverable_bytes


def test_sums_global_and_windows_storage():
    stats = {
        "global_caches": [{"size_bytes": 1_000}, {"size_bytes": 2_000}],
        "windows_storage": [{"size_bytes": 500}],
        "wsl_distros": [],
        "docker_df": [],
    }
    assert total_recoverable_bytes(stats) == 3_500


def test_wsl_vhdx_size_is_not_counted_as_recoverable():
    # A 40 GB vhdx must not inflate the headline number: compaction
    # returns only slack space, not the whole disk file.
    stats = {
        "global_caches": [{"size_bytes": 1_000}],
        "windows_storage": [],
        "wsl_distros": [{"size_bytes": 40_000_000_000}],
        "docker_df": [],
    }
    assert total_recoverable_bytes(stats) == 1_000


def test_docker_df_entries_are_not_counted():
    # docker_df carries unparsed size strings, not byte counts.
    stats = {
        "global_caches": [],
        "windows_storage": [{"size_bytes": 250}],
        "wsl_distros": [],
        "docker_df": [{"Type": "Images", "Size": "5.2GB"}],
    }
    assert total_recoverable_bytes(stats) == 250


def test_empty_stats_is_zero():
    assert total_recoverable_bytes({}) == 0
    assert total_recoverable_bytes({"global_caches": [], "windows_storage": []}) == 0


def test_missing_size_bytes_counts_as_zero():
    stats = {
        "global_caches": [{"name": "NPM Cache"}],
        "windows_storage": [{"name": "User Temp", "size_bytes": 100}],
    }
    assert total_recoverable_bytes(stats) == 100
