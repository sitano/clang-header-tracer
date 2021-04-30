Clang headers trace renderer
===

    $ clang -std=c++20 -I seastar/include -I ./ -I build/dev/gen -I abseil/ -I build/dev/seastar/gen/include -DXXH_PRIVATE_API -H "$SOURCE_FILE" 2>&1 | rg '^[.]+ '

or

    $ cd scylla
    $ ./trace.sh main.cc

Then

    $ ./parse_headers_trace.py --file ./scylla_headers_graph_dep --max-level 100500 --base scylla --collapse abseil/absl /usr/include/boost /usr/include/c++ /usr/include/bits /usr/include/sys /usr/include/asm /usr/include/asm-generic /usr/include/rapidjson/internal --include ~/Projects ~/Projects/scylla/build/dev ~/Projects/scylla/seastar/include ~/Projects/scylla/build/dev/seastar/gen/include --output 1.dot
    $ xdot 1.dot -f fdp
