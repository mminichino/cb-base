# Couchbase Quick Connect for Python 1.0.0
Couchbase connection manager. Simplifies connecting to a Couchbase cluster and performing data and management operations.

## Installing
```
$ pip install cbcbase
```

## API Usage
Connecting to a Couchbase collection, creating the bucket, scope, and collection if they do not exist.
```
session = (CBSession(hostname, username, password)
                   .session()
                   .connect_bucket(bucket, ram_quota=256, replicas=1, create=True)
                   .connect_scope(scope, create=True)
                   .connect_collection(collection, create=True))
```

Connecting to an existing Couchbase collection.
```
session = (CBSession(hostname, username, password)
                   .session()
                   .connect_bucket(bucket)
                   .connect_scope(scope)
                   .connect_collection(collection))
```
