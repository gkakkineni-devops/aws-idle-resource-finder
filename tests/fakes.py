"""Tiny stand-ins for the boto3 clients, so the tests need no AWS and no network."""


class FakePaginator:
    def __init__(self, pages, calls, name):
        self.pages = pages
        self.calls = calls
        self.name = name

    def paginate(self, **kwargs):
        self.calls.append((self.name, kwargs))
        return iter(self.pages)


class FakeEC2:
    """Hands back whatever you give it, split into two pages to prove paging works."""

    def __init__(self, volumes=(), addresses=(), snapshots=(), instances=()):
        self.calls = []
        self.addresses = list(addresses)
        self.data = {
            "describe_volumes": ("Volumes", list(volumes)),
            "describe_snapshots": ("Snapshots", list(snapshots)),
            "describe_instances": (
                "Reservations",
                [{"Instances": [i]} for i in instances],
            ),
        }

    def get_paginator(self, name):
        key, items = self.data[name]
        middle = len(items) // 2
        pages = [{key: items[:middle]}, {key: items[middle:]}]
        return FakePaginator(pages, self.calls, name)

    def describe_addresses(self):
        return {"Addresses": self.addresses}


class FakeS3:
    def __init__(self):
        self.puts = []

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
