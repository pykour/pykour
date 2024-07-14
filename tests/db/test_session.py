import os

import pytest
from pykour.db.session import Session


# テスト用のSQLiteデータベースファイル名
TEST_DB = "test.db"


@pytest.fixture
def sqlite_session():
    # テスト用のセッションを作成
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    session = Session(db_type="sqlite", url=TEST_DB)
    yield session
    # テスト終了後にクリーンアップ
    session.close()
    os.remove(TEST_DB)


def test_execute(sqlite_session):
    # テーブルの作成
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()

    # データの挿入
    sqlite_session.execute("INSERT INTO test (name) VALUES (?)", ("Alice",))
    sqlite_session.commit()

    # データの取得
    sqlite_session.execute("SELECT * FROM test")
    result = sqlite_session.fetchall()
    assert len(result) == 1
    assert result[0][1] == "Alice"


def test_fetchone(sqlite_session):
    # テーブルの作成
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()

    # データの挿入
    sqlite_session.execute("INSERT INTO test (name) VALUES (?)", ("Bob",))
    sqlite_session.commit()

    # データの取得
    sqlite_session.execute("SELECT * FROM test WHERE name = ?", ("Bob",))
    result = sqlite_session.fetchone()
    assert result[1] == "Bob"


def test_commit_and_rollback(sqlite_session):
    # テーブルの作成
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()

    # データの挿入
    sqlite_session.execute("INSERT INTO test (name) VALUES (?)", ("Charlie",))
    sqlite_session.rollback()

    # ロールバック後のデータ確認
    sqlite_session.execute("SELECT * FROM test WHERE name = ?", ("Charlie",))
    result = sqlite_session.fetchall()
    assert len(result) == 0


def test_close(sqlite_session):
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()
    sqlite_session.close()

    with pytest.raises(AttributeError):
        sqlite_session.execute("SELECT * FROM test")
