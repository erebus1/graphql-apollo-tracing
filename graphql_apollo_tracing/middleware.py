import base64
import sys
from collections import defaultdict

import time
from functools import partial
from .reports_pb2 import Trace
from google.protobuf.timestamp_pb2 import Timestamp

PY37 = sys.version_info[0:2] >= (3, 7)


class TracingMiddleware(object):
    def __init__(self):
        self.resolver_stats = list()
        self.reset()

    def reset(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.reset()
        self.start_time = self.now()

    def end(self):
        self.end_time = self.now()

    def now(self):
        if PY37:
            return time.time_ns()

        return int(time.time() * 1000000000)

    @property
    def duration(self):
        if not self.end_time:
            raise ValueError("Tracing has not ended yet!")

        return self.end_time - self.start_time

    # todo limit depth?
    def _get_node(self, node, parent_node, parent_id_child_map):
        node_kwargs = dict(
            start_time=node['start_time'],
            end_time=node['end_time'],
            type=node["type"],
            parent_type=node.get('parent_type') or (parent_node and parent_node['type'])
        )
        if 'index' in node:
            node_kwargs['index'] = node['index']
        elif 'response_name' in node:
            node_kwargs['response_name'] = node['response_name']
        node_key = ";".join(map(str, node['path']))
        if parent_id_child_map[node_key]:
            children = []
            for child_node in parent_id_child_map[node_key]:
                children.append(self._get_node(child_node, node, parent_id_child_map))
            node_kwargs['child'] = children

        if node.get("original_field_name"):
            node_kwargs["original_field_name"] = node.get("original_field_name")
        return Trace.Node(**node_kwargs)

    def _create_parent_intermediate_node(self, item, parent_path):
        return {
            "index": parent_path[-1],
            "path": parent_path,
            "parent_type": None,
            "original_field_name": None,
            "type": item['parent_type'],
            "start_time": item['start_time'],
            "end_time": item['start_time'],
            "parent_id": ";".join(map(str, parent_path[:-1]))
        }

    def _get_execution_graph_stats(self):
        intermediate_nodes_map = {}
        for item in self.resolver_stats:
            parent_path = item['path'][:-1]
            if isinstance(parent_path and parent_path[-1], int):
                intermediate_node_id = ";".join(map(str, parent_path))
                if intermediate_node_id not in intermediate_nodes_map:
                    intermediate_nodes_map[intermediate_node_id] = \
                        self._create_parent_intermediate_node(item, parent_path)
            item['parent_id'] = ";".join(map(str, parent_path))
            item['response_name'] = item['original_field_name']

        self.resolver_stats += list(intermediate_nodes_map.values())

        parent_id_to_children_map = defaultdict(list)
        for item in self.resolver_stats:
            parent_id_to_children_map[item['parent_id']].append(item)

        root_nodes = parent_id_to_children_map['']
        if len(root_nodes) != 1:
            # smth went wrong
            return Trace.Node()

        return self._get_node(root_nodes[0], None, parent_id_to_children_map)

    def get_tracing_ftv1(self):
        try:
            res = Trace(
                start_time=Timestamp(seconds=self.start_time // 10 ** 9, nanos=self.start_time % 10 ** 9),
                end_time=Timestamp(seconds=self.end_time // 10 ** 9, nanos=self.start_time % 10 ** 9),
                duration_ns=self.duration,
                root=self._get_execution_graph_stats()
            )
            return base64.b64encode(res.SerializeToString()).decode()
        except:
            return ''

    def _after_resolve(self, start_time, resolver_stats, info, data):
            try:
                stat = {
                    "path": info.path,
                    "parent_type": str(info.parent_type),
                    "original_field_name": info.field_name,  # todo support alias?
                    "type": str(info.return_type),
                    "start_time": start_time - self.start_time,
                    "end_time": self.now() - self.start_time,
                }  # todo also will not track loaders correctly
                resolver_stats.append(stat)
            except:
                pass
            return data

    def resolve(self, _next, root, info, *args, **kwargs):
        start = self.now()
        on_result_f = partial(self._after_resolve, start, self.resolver_stats, info)
        return _next(root, info, *args, **kwargs).then(on_result_f)
