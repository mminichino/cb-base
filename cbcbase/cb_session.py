##
##

import time
import hashlib
import logging
from datetime import timedelta
from typing import List
from couchbase.auth import PasswordAuthenticator
from couchbase.bucket import Bucket
from couchbase.diagnostics import PingState
from couchbase.exceptions import BucketAlreadyExistsException, ScopeAlreadyExistsException, CollectionAlreadyExistsException
from couchbase.logic.n1ql import QueryScanConsistency
from couchbase.management.buckets import BucketManager, CreateBucketSettings
from couchbase.management.collections import CollectionSpec
from couchbase.management.options import CreatePrimaryQueryIndexOptions
from couchbase.management.logic.buckets_logic import BucketType, StorageBackend, EvictionPolicyType, CompressionMode, ConflictResolutionType
from couchbase.options import ClusterTimeoutOptions, ClusterOptions, TLSVerifyMode, AnalyticsOptions
from couchbase.cluster import Cluster, QueryOptions
from pytoolbase.retry import retry
from cbcbase.logic.cb_index import CBQueryIndex

logger = logging.getLogger('cbcbase.logic.cb_session')
logger.addHandler(logging.NullHandler())


class CBSession(object):

    def __init__(self, hostname: str, username: str, password: str, ssl=True, kv_timeout: int = 5, query_timeout: int = 60):
        self.cluster_node_count = None
        self._cluster = None
        self._bucket = None
        self._scope = None
        self._collection = None
        self._bucket_name = None
        self._scope_name = "_default"
        self._collection_name = "_default"
        self.ssl = ssl
        self.kv_timeout = kv_timeout
        self.query_timeout = query_timeout
        self.hostname = hostname
        self.username = username
        self.password = password

        self.auth = PasswordAuthenticator(self.username, self.password)
        self.timeouts = ClusterTimeoutOptions(query_timeout=timedelta(seconds=query_timeout),
                                              kv_timeout=timedelta(seconds=kv_timeout),
                                              bootstrap_timeout=timedelta(seconds=kv_timeout * 2),
                                              resolve_timeout=timedelta(seconds=kv_timeout),
                                              connect_timeout=timedelta(seconds=kv_timeout),
                                              management_timeout=timedelta(seconds=kv_timeout * 2))

        if self.ssl:
            self.prefix = "https://"
            self.cb_prefix = "couchbases://"
            self.srv_prefix = "_couchbases._tcp."
            self.admin_port = 18091
            self.node_port = 19102
        else:
            self.prefix = "http://"
            self.cb_prefix = "couchbase://"
            self.srv_prefix = "_couchbase._tcp."
            self.admin_port = 8091
            self.node_port = 9102

        self.cluster_options = ClusterOptions(self.auth,
                                              timeout_options=self.timeouts,
                                              enable_tls=self.ssl,
                                              tls_verify=TLSVerifyMode.NO_VERIFY)

    @property
    def cb_connect_string(self):
        connect_string = self.cb_prefix + self.hostname
        logger.debug(f"Connect string: {connect_string}")
        return connect_string

    @property
    def keyspace(self):
        return f"{self._bucket_name}.{self._scope_name}.{self._collection_name}"

    def session(self):
        self._cluster = Cluster.connect(self.cb_connect_string, self.cluster_options)
        self._cluster.wait_until_ready(timedelta(seconds=5))
        return self

    def disconnect(self):
        self._bucket = None
        self._scope = None
        self._collection = None
        self._bucket_name = None
        self._scope_name = "_default"
        self._collection_name = "_default"
        if self._cluster:
            self._cluster.close()
        self._cluster = None

    def connect_bucket(self,
                       bucket_name: str,
                       create: bool = False,
                       replicas: int = 1,
                       ram_quota: int = 128,
                       flush: bool = False,
                       bucket_storage: StorageBackend = StorageBackend.COUCHSTORE,
                       ttl: int = 0):
        if create:
            self.create_bucket(bucket_name, replicas, ram_quota, flush, bucket_storage, ttl)
        self._bucket = self._cluster.bucket(bucket_name)
        self._bucket_name = bucket_name
        return self

    def connect_scope(self, scope_name: str, create: bool = False):
        if create:
            self.create_scope(self._bucket_name, scope_name)
        self._scope = self._bucket.scope(scope_name)
        self._scope_name = scope_name
        return self

    def connect_collection(self, collection_name: str, create: bool = False):
        if create:
            self.create_collection(self._bucket_name, self._scope_name, collection_name)
        self._collection = self._scope.collection(collection_name)
        self._collection_name = collection_name
        return self

    def create_bucket(self,
                      bucket_name: str,
                      replicas: int = 1,
                      ram_quota: int = 128,
                      flush: bool = False,
                      bucket_storage: StorageBackend = StorageBackend.COUCHSTORE,
                      ttl: int = 0):
        bucket_manager: BucketManager = self._cluster.buckets()
        try:
            bucket_manager.create_bucket(CreateBucketSettings(
                    name=bucket_name,
                    flush_enabled=flush,
                    replica_index=False,
                    ram_quota_mb=ram_quota,
                    num_replicas=replicas,
                    bucket_type=BucketType.COUCHBASE,
                    eviction_policy=EvictionPolicyType.VALUE_ONLY,
                    max_ttl=ttl,
                    compression_mode=CompressionMode.PASSIVE,
                    conflict_resolution_type=ConflictResolutionType.SEQUENCE_NUMBER,
                    storage_backend=bucket_storage,
                ))
        except BucketAlreadyExistsException:
            pass

    def bucket_wait_until_ready(self, bucket_name: str, retry_count: int = 30, wait: float = 0.5):
        bucket = self._cluster.bucket(bucket_name)
        for retry_number in range(retry_count + 1):
            if self.bucket_check(bucket):
                return True
            else:
                if retry_number == retry_count:
                    return False
                time.sleep(wait)

    @staticmethod
    def bucket_check(bucket: Bucket):
        result = bucket.ping()
        for endpoint, reports in result.endpoints.items():
            for report in reports:
                if not report.state == PingState.OK:
                    return False
        return True

    def drop_bucket(self, bucket_name: str):
        bucket_manager: BucketManager = self._cluster.buckets()
        bucket_manager.drop_bucket(bucket_name)

    def create_scope(self, bucket_name: str, scope_name: str):
        if scope_name == '_default':
            return
        bucket: Bucket = self._cluster.bucket(bucket_name)
        collection_manager = bucket.collections()
        try:
            collection_manager.create_scope(scope_name)
        except ScopeAlreadyExistsException:
            pass

    def create_collection(self, bucket_name: str, scope_name: str, collection_name: str):
        if collection_name == '_default':
            return
        bucket: Bucket = self._cluster.bucket(bucket_name)
        collection_manager = bucket.collections()
        collection_spec = CollectionSpec(collection_name, scope_name=scope_name)
        try:
            collection_manager.create_collection(collection_spec)
        except CollectionAlreadyExistsException:
            pass

    def get_bucket(self, bucket_name: str):
        return self._cluster.bucket(bucket_name)

    @retry()
    def create_primary_index(self, bucket_name: str, scope_name: str, collection_name: str, replicas: int = 1, deferred: bool = False, timeout: int = 60):
        index_options = CreatePrimaryQueryIndexOptions()
        index_options.update(deferred=deferred)
        index_options.update(timeout=timedelta(seconds=timeout))
        index_options.update(num_replicas=replicas)
        index_options.update(ignore_if_exists=True)
        index_options.update(scope_name=scope_name)
        index_options.update(collection_name=collection_name)

        qim = self._cluster.query_indexes()
        qim.create_primary_index(bucket_name, index_options)

    @retry()
    def create_index(self, bucket_name: str, scope_name: str, collection_name: str, fields: List[str], replicas: int = 1, deferred: bool = False, timeout: int = 60):
        index_options = CreatePrimaryQueryIndexOptions()
        index_options.update(deferred=deferred)
        index_options.update(timeout=timedelta(seconds=timeout))
        index_options.update(num_replicas=replicas)
        index_options.update(ignore_if_exists=True)
        index_options.update(scope_name=scope_name)
        index_options.update(collection_name=collection_name)

        field_str = ','.join(fields)
        hash_string = f"{bucket_name}_{scope_name}_{collection_name}_{field_str}"
        name_part = hashlib.shake_256(hash_string.encode()).hexdigest(4)
        index_name = f"{collection_name}_{name_part}_ix"

        qim = self._cluster.query_indexes()
        qim.create_index(bucket_name, index_name, fields, index_options)

        return index_name

    def index_list_all(self):
        all_list = []
        query_str = "SELECT * FROM system:indexes"
        results = self.query(query_str)

        for row in results:
            for key, value in row.items():
                entry = CBQueryIndex.from_dict(value)
                all_list.append(entry)

        return all_list

    def collection_has_primary_index(self):
        index_name = '#primary'
        index_list = self.index_list_all()
        for item in index_list:
            if index_name == '#primary':
                if (item.keyspace_id == self._collection_name or item.keyspace_id == self._bucket_name) and item.name == '#primary':
                    return True
            elif item.name == index_name:
                return True
        return False

    def collection_has_index(self, index_name: str):
        index_list = self.index_list_all()
        for item in index_list:
            if item.name == index_name:
                return True
        return False

    def bucket_name(self, bucket_name: str):
        self._bucket_name = bucket_name
        return self

    def scope_name(self, scope_name: str):
        self._scope_name = scope_name
        return self

    def collection_name(self, collection_name: str):
        self._collection_name = collection_name
        return self

    def get(self, doc_id: str):
        result = self._collection.get(doc_id)
        return result.content_as[dict]

    def put(self, doc_id: str, document: dict):
        result = self._collection.upsert(doc_id, document)
        return result.cas

    def query(self, query: str, consistent: bool = True):
        if consistent:
            consistency = QueryScanConsistency.REQUEST_PLUS
        else:
            consistency = QueryScanConsistency.NOT_BOUNDED
        contents = []
        result = self._cluster.query(query, QueryOptions(query_context=f"default:{self._bucket_name}.{self._scope_name}", scan_consistency=consistency))
        for item in result:
            contents.append(item)
        return contents

    def analytics_query(self, query: str):
        contents = []
        result = self._cluster.analytics_query(query, AnalyticsOptions(query_context=f"default:{self._bucket_name}.{self._scope_name}"))
        for item in result:
            contents.append(item)
        return contents
