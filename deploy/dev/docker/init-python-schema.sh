#!/bin/sh
set -eu

# MySQL 的官方 entrypoint 会以 root 身份执行此脚本。测试 schema 是 H2
# 兼容方言；这里仅在开发/QA 容器内做确定性的索引语法转换，再交给 mysql
# 客户端执行。生产环境请使用已审计的 schema 快照和 Alembic 流程。
echo "event=python_schema_bootstrap_started database=${MYSQL_DATABASE:-unknown}"

source_file=/opt/schema-test.sql
converted_file=/tmp/schema-test.mysql.sql
if [ ! -r "$source_file" ]; then
  echo "event=python_schema_bootstrap_failed reason=source_missing" >&2
  exit 1
fi

# MySQL 8 不接受 CREATE [UNIQUE] INDEX IF NOT EXISTS；表定义仍保留 IF
# NOT EXISTS，保证重启/重放时幂等。
sed -E 's/CREATE (UNIQUE )?INDEX IF NOT EXISTS/CREATE \1INDEX/g' \
  "$source_file" >"$converted_file"

mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" \
  <"$converted_file"
echo "event=python_schema_bootstrap_completed result=success"
