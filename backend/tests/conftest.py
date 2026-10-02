"""H03 回归测试引导。

测试机通常没有 docker / 系统 PostgreSQL，这里用 pgserver wheel（自包含
PostgreSQL 16）在临时目录拉起一个真实实例，并在任何业务模块 import 之前
把 DATABASE_URL 指向它（db.DSN 在 import 时固化）。
"""

import os
import tempfile

_pg_server = None


def _bootstrap_postgres():
    try:
        import pgserver
    except ImportError:
        return None
    try:
        # initdb 要求数据目录必须为空，runtime 目录要放在数据目录之外
        data_dir = tempfile.mkdtemp(prefix="h03-pg-data-")
        runtime_dir = tempfile.mkdtemp(prefix="h03-pg-run-")
        os.environ.setdefault("XDG_RUNTIME_DIR", runtime_dir)
        server = pgserver.get_server(data_dir, cleanup_mode="stop")
    except Exception:
        return None
    os.environ["DATABASE_URL"] = server.get_uri()
    return server


_pg_server = _bootstrap_postgres()

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def pg_server():
    if _pg_server is None:
        pytest.skip("pgserver 不可用，跳过数据库端到端对拍")
    return _pg_server
