#!/usr/bin/python3

import argparse
import os.path
import re
import sys
import json

parser = argparse.ArgumentParser()
parser.add_argument('--file', required=True)
parser.add_argument('--base', default=".")
parser.add_argument('--max-level', dest='max_level', type=int, default=10000)
parser.add_argument('--print-tree', dest='print_tree', type=bool, default=False)
parser.add_argument('--output', dest='output', type=str, default='')
parser.add_argument('--collapse', nargs='*', default=[])
parser.add_argument('--include', nargs='*', default=[])

args = parser.parse_args()

edge_type_explicit = 0
edge_type_transitive = 1


class Edge:
    # node -> node, type = [explicit, transitive]
    def __init__(self, _from, _to, _type):
        self.node_from = _from
        self.node_to = _to
        self.edge_type = _type


class Node:
    def __init__(self, name):
        self.name = name
        self.edges = {}

    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class Scope:
    def __init__(self, prefix):
        self.prefix = prefix
        self.nodes = {}
        self.child = {}

    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__)


root = Scope(".cc")
tree = {root.prefix: root}
stack = [root.prefix]


def try_push_node(fullpath):
    lcc = os.path.dirname(fullpath)
    if lcc != root.prefix:
        lccs = lcc.split("/")
        parent = root
        for item in lccs:
            prefix = item
            if parent != root:
                prefix = parent.prefix + "/" + item
            if prefix not in parent.child:
                obj = Scope(prefix)
                parent.child[prefix] = obj
                tree[prefix] = obj
            parent = parent.child[prefix]
    obj = root
    if lcc:
        obj = tree[lcc]
    if fullpath not in obj.nodes:
        obj.nodes[fullpath] = Node(fullpath)
    return obj.nodes[fullpath]


def push_edge(_from, _to, edge_type):
    node_from = try_push_node(_from)
    node_to = try_push_node(_to)
    if _to not in node_from.edges:
        node_from.edges[_to] = Edge(node_from, node_to, edge_type)


def depth(line):
    return line.find(' ')


def pop_until(depth):
    while len(stack) > depth:
        stack.pop()


def update_stack(name, depth, base):
    if base + depth <= len(stack):
        pop_until(base + depth - 1)
    stack.append(name)


def get_name(line):
    name = line[line.find(' ') + 1:].strip()
    if name[0] == '.':
        name = args.base + '/' + name
    if name.startswith('build/'):
        # cut build/dev/
        name = name[name.find('/', len('build/'))+1:]
        if name.startswith('seastar/gen/include/'):
            name = name[len('seastar/gen/include/'):]
        # else:
        #    if name.startswith('gen/'):
        #        name = name[len('gen/'):]
        #    name = args.base + '/' + name
    if name.startswith('seastar/include/'):
        name = name[len('seastar/include/'):]

    name = os.path.normpath(name)

    for prefix in args.collapse:
        if name.startswith(prefix):
            name = prefix

    return name


dot_format = re.compile('[^a-zA-Z0-9/.+_-]')


def dot_name(name):
    return dot_format.sub('_', name)


def fill_tree():
    fd = open(args.file, 'r')
    stack_base = len(stack)
    for line in fd.readlines():
        line_depth = depth(line)
        if line_depth <= args.max_level:
            name = get_name(line)
            update_stack(name, line_depth, stack_base)
            push_edge(stack[-2:][0], stack[-1:][0], edge_type_explicit)
            # print(name)
            # print(stack)
    fd.close()


include_format = re.compile('\W*#include\W+["<](.+)[">]')


def dfs_transitive_includes(parent, visited):
    for item in parent.child.values():
        dfs_transitive_includes(item, visited)

    for node in parent.nodes.values():
        path = node.name
        if not os.path.isfile(path):
            for inc in args.include:
                if os.path.isfile(inc + '/' + path):
                    path = inc + '/' + path
                    break

        if not os.path.isfile(path):
            print("skipped: " + node.name, file=sys.stderr)
            continue

        file = open(path, mode='r')
        for item in include_format.findall(file.read()):
            # TODO: find target in fs
            if item in visited:
                continue
            visited[item] = True
            # TODO: put an edge into the tree
            print(item)
        file.close()


fill_tree()
dfs_transitive_includes(root, {})

if args.print_tree:
    print(root)


def render():
    f = open(args.output, 'w') if args.output else sys.stdout

    f.write('digraph G {\n')
    f.write('  node [fontname=Helvetica, fontsize=10];\n\n')

    def render_nodes(parent, indent):
        indentstd = '  ' * indent
        for node in parent.nodes.values():
            f.write(indentstd + '"%s";\n' % dot_name(node.name))

    def render_edges(parent, indent):
        indentstd = '  ' * indent
        for node in parent.nodes.values():
            for edge in node.edges.values():
                attr = ""
                if edge.edge_type != edge_type_explicit:
                    attr = " [color=blue]"
                f.write(indentstd +
                        '"%s" -> "%s"%s;\n' % (dot_name(edge.node_from.name), dot_name(edge.node_to.name), attr))

    def dfs_nodes(parent, indent, cluster):
        def to_render(node):
            return node is not root and node.prefix

        indentstd = '  ' * indent

        if to_render(parent):
            f.write("%ssubgraph cluster_%d {\n" % (indentstd, cluster))
            f.write("%s  label=\"%s\";\n" % (indentstd, parent.prefix))
            cluster += 1

        for item in parent.child.values():
            cluster = dfs_nodes(item, indent+1, cluster)
            f.write("%s\n" % indentstd)

        render_nodes(parent, indent + 1)

        if to_render(parent):
            f.write("%s}\n" % indentstd)

        return cluster

    def dfs_edges(parent):
        for item in parent.child.values():
            dfs_edges(item)

        render_edges(parent, 1)

    dfs_nodes(root, 1, 0)
    f.write('\n')
    dfs_edges(root)

    f.write('}\n')
    f.close()


render()
