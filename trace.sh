SOURCE_FILE=$1

if [ -z "$SOURCE_FILE" ]; then
  SOURCE_FILE="main.cc"
fi

clang -std=c++20 -I seastar/include -I ./ -I build/dev/gen -I abseil/ -I build/dev/seastar/gen/include -DXXH_PRIVATE_API -H "$SOURCE_FILE" 2>&1 | rg '^[.]+ '
