import re
from collections import defaultdict

def nl2sql(statements):
    sql_outputs = []

    for nl in statements:
        nl_lower = nl.strip().lower()
        if not nl_lower:
            continue

        # -------------------- INSERT --------------------
        if re.search(r"\b(add|insert|make|create|fill|record|save|store|put|register)\b", nl_lower):
            grouped_inserts = defaultdict(list)
            table_match = re.search(r"\b(add|insert|make|create|fill|record|save|store|put|register)\s+(?:a|an|new)?\s*(\w+)", nl_lower)
            if table_match:
                table = table_match.group(2)
                if not table.endswith("s"):
                    table += "s"
                pairs = re.findall(r"(\w+)\s*(is|=|as|to)\s*['\"]?([^,;\n]+?)['\"]?(?=,|$)", nl_lower)
                if pairs:
                    columns = tuple(col.strip() for col, _, _ in pairs)
                    values = tuple(val.strip() for _, _, val in pairs)
                    grouped_inserts[(table, columns)].append(values)
                    for (t, cols), rows in grouped_inserts.items():
                        col_str = ", ".join(cols)
                        val_str = ",\n       ".join(
                            f"({', '.join(f'\'{v}\'' for v in row)})" for row in rows
                        )
                        sql_outputs.append(f"INSERT INTO {t} ({col_str}) VALUES\n       {val_str};")
            continue

        # -------------------- UPDATE --------------------
        elif re.search(r"\b(update|change|modify|edit|alter|adjust|revise|replace)\b", nl_lower):
            update_match = re.search(r"\b(update|change|modify|edit|alter|adjust|revise|replace)\b\s+(?:a|an|the)?\s*(\w+)", nl_lower)
            if update_match:
                table = update_match.group(2)
                if not table.endswith("s"):
                    table += "s"
                where_clause = ""
                where_match = re.search(r"\bwhere\b\s+(.+)", nl_lower)
                if where_match:
                    where_pairs = re.findall(r"(\w+)\s*(is|=|as|to)\s*['\"]?([^,;]+?)['\"]?(?:,|$)", where_match.group(1))
                    if where_pairs:
                        conditions = [f"{col} = '{val.strip()}'" for col, _, val in where_pairs]
                        where_clause = " WHERE " + " AND ".join(conditions)
                set_match = re.search(r"\b(set|change|update|modify|edit|alter|adjust|revise|replace)\b\s+(.+)", nl_lower)
                set_pairs = []
                if set_match:
                    set_pairs = re.findall(r"(\w+)\s*(is|=|as|to)\s*['\"]?([^,;]+?)['\"]?(?:,|$)", set_match.group(2))
                set_clause = ", ".join(f"{col} = '{val.strip()}'" for col, _, val in set_pairs)
                sql_outputs.append(f"UPDATE {table} SET {set_clause}{where_clause};")
            continue

        # -------------------- DELETE --------------------
        elif re.search(r"\b(delete|remove|erase|drop|clear|discard|eliminate|terminate|destroy|cut|wipe)\b", nl_lower):
            delete_match = re.search(r"\b(delete|remove|erase|drop|clear|discard|eliminate|terminate|destroy|cut|wipe)\b\s+(?:a|an|the)?\s*(\w+)", nl_lower)
            if delete_match:
                table = delete_match.group(2)
                if not table.endswith("s"):
                    table += "s"
                where_clause = ""
                where_match = re.search(r"\bwhere\b\s+(.+)", nl_lower)
                if where_match:
                    where_pairs = re.findall(r"(\w+)\s*(is|=|as|to)\s*['\"]?([^,;]+?)['\"]?(?:,|$)", where_match.group(1))
                    if where_pairs:
                        conditions = [f"{col} = '{val.strip()}'" for col, _, val in where_pairs]
                        where_clause = " WHERE " + " AND ".join(conditions)
                if where_clause:
                    sql_outputs.append(f"DELETE FROM {table}{where_clause};")
                else:
                    sql_outputs.append(f"DELETE FROM {table}; -- ⚠️ Warning: no WHERE clause")
            continue

        # -------------------- SELECT --------------------
        elif re.search(r"\b(select|get|show|fetch|give|giveme)\b", nl_lower):
            def parse_select(query):
                query = query.strip().lower()
                query = re.sub(r"\s+and\s+", ", ", query)

                # Pattern for SELECT
                pattern = r"(select|get|show|fetch|give)\s+(.+?)\s+from\s+([a-z_][a-z0-9_]*)"
                m = re.match(pattern, query)
                if not m:
                    return f"unknown error"

                columns_raw = m.group(2).strip()

                # ---- Handle "all" and "all <column>" ----
                m_all_col = re.match(r"all\s+([a-z_]+)s?$", columns_raw)
                if columns_raw == "all":
                    columns = "*"
                elif m_all_col:
                    columns = m_all_col.group(1)  # singular column
                else:
                    columns = ", ".join([c.strip() for c in columns_raw.split(",")])

                table = m.group(3).strip()

                # Optional WHERE clause
                where_clause = ""
                where_match = re.search(r"\bwhere\b\s+(.+)", query)
                if where_match:
                    where_raw = where_match.group(1)
                    ops = [
                        (r"\bis not equal to\b", "<>"), (r"\bnot equal to\b", "<>"),
                        (r"\bis equal to\b", "="), (r"\bequal to\b", "="),
                        (r"\bgreater than or equal to\b", ">="), (r"\bless than or equal to\b", "<="),
                        (r"\bgreater than\b", ">"), (r"\bless than\b", "<"),
                        (r"\bis\b", "="), (r"\blike\b", "LIKE"), (r"\bbetween\b", "BETWEEN"),
                        (r"\bin\b", "IN"), (r"\bnot\b", "NOT"), (r"\bor\b", "OR"), (r"\band\b", "AND")
                    ]
                    for p,r in ops:
                        where_raw = re.sub(p,r,where_raw)
                    # Quote string values
                    where_raw = re.sub(r"= ([^ \)]+)", lambda x: f"= '{x.group(1)}'" if not x.group(1).replace('.','',1).isdigit() else f"= {x.group(1)}", where_raw)
                    where_raw = re.sub(r"<> ([^ \)]+)", lambda x: f"<> '{x.group(1)}'" if not x.group(1).replace('.','',1).isdigit() else f"<> {x.group(1)}", where_raw)
                    where_raw = re.sub(r"LIKE ([^ \)]+)", lambda x: f"LIKE '{x.group(1)}'", where_raw)
                    where_raw = re.sub(r"IN\s*\(([^)]+)\)", lambda x: "IN (" + ", ".join(f"'{v.strip()}'" for v in x.group(1).split(",")) + ")", where_raw)
                    where_clause = f" WHERE {where_raw}"

                # Optional ORDER BY
                order_clause = ""
                order_match = re.search(r"\border by\b\s+(.+)", query)
                if order_match:
                    order_raw = order_match.group(1)
                    items = []
                    for col in order_raw.split(","):
                        col = col.strip()
                        if "desc" in col or "descending" in col:
                            col_name = col.replace("desc","").replace("descending","").strip()
                            items.append(f"{col_name} DESC")
                        elif "asc" in col or "ascending" in col:
                            col_name = col.replace("asc","").replace("ascending","").strip()
                            items.append(f"{col_name} ASC")
                        else:
                            items.append(f"{col} ASC")
                    order_clause = " ORDER BY " + ", ".join(items)

                return f"SELECT {columns} FROM {table}{where_clause}{order_clause};"

            sql_outputs.append(parse_select(nl_lower))
            continue

        # Unknown statement
        sql_outputs.append(f"unknown error")

    return sql_outputs