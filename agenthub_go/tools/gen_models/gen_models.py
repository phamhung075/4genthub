import sys

sys.path.insert(0, "/home/daihu/__projects__/4genthub/agenthub_main/src")
import os
import re
import inspect
import json

os.environ.setdefault("DATABASE_TYPE", "postgresql")
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
from fastmcp.task_management.infrastructure.database.database_config import Base

INIT = {
    "id": "ID",
    "uuid": "UUID",
    "url": "URL",
    "api": "API",
    "ai": "AI",
    "json": "JSON",
    "http": "HTTP",
    "ip": "IP",
    "sql": "SQL",
}


def camel(n):
    return "".join(INIT.get(p, p.capitalize()) for p in n.split("_"))


def cls_for(table):
    for c in Base.registry.mappers:
        if c.local_table is table:
            return c.class_.__name__
    raise KeyError(table.name)


def gotype(col):
    t = type(col.type).__name__
    base = {
        "String": "string",
        "Text": "string",
        "UnifiedUUID": "string",
        "Integer": "int64",
        "Boolean": "bool",
        "Float": "float64",
        "DateTime": "time.Time",
        "JSON": "json.RawMessage",
        "Enum": "string",
    }[t]
    if col.nullable and base not in ("json.RawMessage",):
        return "*" + base
    return base


def default_spec(col):
    d = col.default
    if d is None:
        return "DefaultNone", ""
    if d.is_callable:
        a = d.arg
        name = getattr(a, "__name__", "")
        if name == "list":
            return "DefaultEmptyList", ""
        if name == "dict":
            return "DefaultEmptyDict", ""
        src = inspect.getsource(a)
        if "uuid.uuid4" in src:
            return "DefaultUUIDv4", ""
        if "replace(tzinfo=None)" in src:
            return "DefaultNowUTCNaive", ""
        if "datetime.now(UTC)" in src:
            return "DefaultNowUTC", ""
        raise SystemExit(
            "unknown callable default " + col.table.name + "." + col.name + " " + src
        )
    v = d.arg
    if isinstance(v, bool):
        return "DefaultBool", "true" if v else "false"
    if isinstance(v, int):
        return "DefaultInt", str(v)
    if isinstance(v, float):
        return "DefaultFloat", repr(v)
    if isinstance(v, str):
        return "DefaultString", json.dumps(v)
    if hasattr(v, "name"):
        return "DefaultEnum", json.dumps(v.name)
    raise SystemExit("unknown default " + repr(v))


out = [
    "// Code generated from infrastructure/database/models.py (SQLAlchemy metadata); DO NOT EDIT.\n",
    'package database\n\nimport (\n\t"encoding/json"\n\t"time"\n)\n',
]
out.append("""
// GlobalSingletonUUID is the global context singleton UUID (used as a reference ID).
const GlobalSingletonUUID = "00000000-0000-0000-0000-000000000001"

// DefaultKind is how a column default is produced on insert (SQLAlchemy client-side default).
type DefaultKind int

const (
	DefaultNone DefaultKind = iota
	DefaultString
	DefaultInt
	DefaultFloat
	DefaultBool
	DefaultEnum // the enum member NAME is stored
	DefaultEmptyList
	DefaultEmptyDict
	DefaultUUIDv4        // str(uuid.uuid4())
	DefaultNowUTC        // datetime.now(UTC)
	DefaultNowUTCNaive   // datetime.now(UTC).replace(tzinfo=None)
)

// ColumnDef describes one mapped column.
type ColumnDef struct {
	Name          string
	Attr          string // Python attribute name (differs from Name for model_metadata)
	GoField       string
	SQLType       string
	Nullable      bool
	PrimaryKey    bool
	Default       DefaultKind
	DefaultValue  string // literal source text for scalar defaults
	ServerDefault string // SQL text, "" when none
	ForeignKey    string // "table.column" or ""
	OnDelete      string
	EnumName      string // PostgreSQL enum type for Enum columns
}

// TableDef describes one mapped table.
type TableDef struct {
	Name    string
	Model   string
	Columns []ColumnDef
	// DDL is the CREATE TABLE statement followed by its CREATE INDEX statements.
	DDL []string
}

// ColumnNames lists the column names in declaration order.
func (t TableDef) ColumnNames() []string {
	names := make([]string, len(t.Columns))
	for i, c := range t.Columns {
		names[i] = c.Name
	}
	return names
}
""")
tables = Base.metadata.sorted_tables
enums = {}
defs = []
for t in tables:
    cls = cls_for(t)
    fields = []
    for c in t.columns:
        fields.append(f'\t{camel(c.name)} {gotype(c)} `db:"{c.name}"`')
    out.append(
        f"\n// {cls} is a row of {t.name}.\ntype {cls} struct {{\n"
        + "\n".join(fields)
        + "\n}\n"
    )
    if "user_id" in t.c and gotype(t.c.user_id) == "string":
        out.append(
            f"\n// GetUserID satisfies repositories.HasUserID (user isolation).\nfunc (r *{cls}) GetUserID() string {{ return r.UserID }}\n"
        )
    if (
        hasattr(Base.registry._class_registry[cls], "touch")
        and "created_at" in t.c
        and "updated_at" in t.c
    ):
        # Timestamp events (timestamp_events.py) apply to mapped classes that define touch(); touch() is a no-op.
        # A zero time.Time is Python None (not yet set).
        out.append(f"""
func (r *{cls}) GetCreatedAt() *time.Time {{
	if r.CreatedAt.IsZero() {{
		return nil
	}}
	return &r.CreatedAt
}}
func (r *{cls}) SetCreatedAt(t *time.Time) {{
	if t == nil {{
		r.CreatedAt = time.Time{{}}
		return
	}}
	r.CreatedAt = *t
}}
func (r *{cls}) GetUpdatedAt() *time.Time {{
	if r.UpdatedAt.IsZero() {{
		return nil
	}}
	return &r.UpdatedAt
}}
func (r *{cls}) SetUpdatedAt(t *time.Time) {{
	if t == nil {{
		r.UpdatedAt = time.Time{{}}
		return
	}}
	r.UpdatedAt = *t
}}
func (r *{cls}) Touch() {{}}
""")
    cols = []
    mapper = [mp for mp in Base.registry.mappers if mp.local_table is t][0]
    for c in t.columns:
        dk, dv = default_spec(c)
        fk = ""
        od = ""
        for f in c.foreign_keys:
            fk = f.target_fullname
            od = f.ondelete or ""
        sd = ""
        if c.server_default is not None:
            arg = c.server_default.arg
            sd = str(arg.text if hasattr(arg, "text") else arg)
        en = ""
        if type(c.type).__name__ == "Enum":
            en = c.type.name
            enums[en] = list(c.type.enums)
        sqlt = str(c.type.compile(dialect=postgresql.dialect()))
        cols.append(
            f'\t\t{{Name: "{c.name}", Attr: "{mapper.get_property_by_column(c).key}", GoField: "{camel(c.name)}", SQLType: {json.dumps(sqlt)}, Nullable: {str(bool(c.nullable)).lower()}, PrimaryKey: {str(bool(c.primary_key)).lower()}, Default: {dk}, DefaultValue: {json.dumps(dv)}, ServerDefault: {json.dumps(sd)}, ForeignKey: {json.dumps(fk)}, OnDelete: {json.dumps(od)}, EnumName: {json.dumps(en)}}},'
        )
    ddl = [
        re.sub(
            r"\s+\n",
            "\n",
            str(CreateTable(t).compile(dialect=postgresql.dialect())).strip(),
        )
    ]
    for ix in sorted(t.indexes, key=lambda i: i.name):
        ddl.append(str(CreateIndex(ix).compile(dialect=postgresql.dialect())).strip())
    ddls = ",\n".join("\t\t\t" + json.dumps(x) for x in ddl)
    defs.append(
        (
            cls,
            f'\t{{Name: "{t.name}", Model: "{cls}", Columns: []ColumnDef{{\n'
            + "\n".join(cols)
            + f"\n\t}}, DDL: []string{{\n{ddls},\n\t}}}},",
        )
    )
out.append(
    "\n// Tables lists every mapped table in dependency (create) order.\nvar Tables = []TableDef{\n"
    + "\n".join(d for _, d in defs)
    + "\n}\n"
)
out.append(
    "\n// EnumTypes maps each PostgreSQL enum type to its labels (enum member names).\nvar EnumTypes = map[string][]string{\n"
    + "".join(
        f'\t"{k}": {{' + ", ".join(json.dumps(x) for x in v) + "},\n"
        for k, v in enums.items()
    )
    + "}\n"
)
open(
    "/home/daihu/__projects__/4genthub/agenthub_go/fastmcp/task_management/infrastructure/database/models.go",
    "w",
).write("".join(out))
print(len(tables), sum(len(t.columns) for t in tables))
