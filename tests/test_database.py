import pytest
import os
import asyncio

from database.dao import Dao

dao = Dao(os.path.join('database', 'tram.db'))

@pytest.mark.asyncio
async def test_build_db():
    with open("conf/schema.sql") as schema:
        await dao.build((schema.read()))
    assert os.path.isfile("database/tram.db") == True

@pytest.mark.asyncio
async def test_insert():
    test_crit = dict(title='Test report',url='https://docs.pytest.org/en/latest/',current_status="needs_review")
    id = await dao.insert('reports', test_crit)
    compare = test_crit.copy()
    compare['uid'] = id
    compare['attack_key'] = None
    pull = await dao.get('reports',test_crit)
    assert pull[0] == compare

@pytest.mark.asyncio
async def test_update():
    test_crit = dict(title='Test report',url='https://docs.pytest.org/en/latest/',current_status="reviewed")
    compare = test_crit.copy()
    compare['uid'] = 1
    compare['attack_key'] = None
    await dao.update('reports', 'uid', 1, dict(current_status="reviewed"))
    pull = await dao.get('reports',test_crit)
    assert pull[0] == compare
    

@pytest.mark.asyncio
async def test_delete():
    test_crit = dict(title='Test report',url='https://docs.pytest.org/en/latest/',current_status="reviewed")
    await dao.delete('reports',dict(uid=1))
    pull = await dao.get('reports',test_crit)
    assert pull == []


@pytest.mark.asyncio
async def test_delete_db():
    os.remove('database/tram.db')
    assert os.path.isfile("database/tram.db") == False

