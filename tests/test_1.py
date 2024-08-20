##
##

import os
import warnings
import time
import pytest
from cbcbase.cb_session import CBSession
from tests.common import start_container, stop_container, run_in_container, document, query_result, image_name


warnings.filterwarnings("ignore")


@pytest.mark.serial
class TestSyncDrv1(object):
    container_id = None

    @classmethod
    def setup_class(cls):
        print("Starting test container")
        platform = f"linux/{os.uname().machine}"
        cls.container_id = start_container(image_name, platform)
        command = ['/bin/bash', '-c', 'test -f /demo/couchbase/.ready']
        while not run_in_container(cls.container_id, command):
            time.sleep(1)
        command = ['cbcutil', 'list', '--host', '127.0.0.1', '--wait']
        run_in_container(cls.container_id, command)
        time.sleep(1)

    @classmethod
    def teardown_class(cls):
        print("Stopping test container")
        stop_container(cls.container_id)
        time.sleep(1)

    @pytest.mark.parametrize("hostname", ["127.0.0.1"])
    @pytest.mark.parametrize("bucket", ["test"])
    @pytest.mark.parametrize("scope, collection", [("_default", "_default"), ("test", "test")])
    @pytest.mark.parametrize("tls", [False, True])
    def test_1(self, hostname, bucket, tls, scope, collection):
        replica_count = 0

        session = (CBSession(hostname, "Administrator", "password")
                   .session()
                   .connect_bucket(bucket, replicas=replica_count, create=True)
                   .connect_scope(scope, create=True)
                   .connect_collection(collection, create=True))

        result = session.get_bucket(bucket)
        assert result is not None

        session.create_primary_index(bucket, scope, collection, replicas=replica_count)
        index_name = session.create_index(bucket, scope, collection, ["data"], replicas=replica_count)

        result = session.collection_has_primary_index()
        assert result is True
        result = session.collection_has_index(index_name)
        assert result is True

        session.put("test::1", document)
        result = session.get("test::1")
        assert result == document

        result = session.query(f"SELECT data FROM {collection}")
        assert result == query_result

        session.put("test::2", document)
        result = session.get("test::2")
        assert result == document
        session.put("test::3", document)
        result = session.get("test::3")
        assert result == document

        session.drop_bucket(bucket)

        session.disconnect()
