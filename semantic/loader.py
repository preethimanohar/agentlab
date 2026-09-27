"""Load the semantic layer and render it as agent context.

The point of the experiment: an agent run in `schema` mode gets `schema_block()`
only; an agent in `schema+semantics` mode also gets `semantics_block()`. If a
definition in metrics.yaml changes, the second agent's answers should change.

    from semantic.loader import SemanticLayer
    sem = SemanticLayer.load()
    print(sem.context(include_semantics=True))
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import yaml

YAML_PATH = Path("semantic/metrics.yaml")
DB_PATH = Path("data/generated/canonical.duckdb")
BASE_TABLES = ("restaurants", "inspections", "violations")


@dataclass
class SemanticLayer:
    spec: dict

    @classmethod
    def load(cls, path: Path = YAML_PATH) -> "SemanticLayer":
        return cls(yaml.safe_load(path.read_text()))

    # --- schema (available in every non-raw mode) ---------------------------
    def schema_block(self, db: Path = DB_PATH) -> str:
        con = duckdb.connect(str(db), read_only=True)
        lines = ["# Database schema (DuckDB)\n"]
        for tbl in BASE_TABLES:
            cols = con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? ORDER BY ordinal_position", [tbl]
            ).fetchall()
            n = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
            lines.append(f"## {tbl}  ({n:,} rows)")
            lines += [f"  {c:<22} {t}" for c, t in cols]
            lines.append("")
        con.close()
        return "\n".join(lines)

    # --- semantics (only in schema+semantics mode) ------------------------
    def semantics_block(self) -> str:
        s = self.spec
        out: list[str] = ["# Semantic definitions (authoritative)\n"]

        out.append("## Entities & grain")
        for name, e in s["entities"].items():
            grain = ", ".join(e["grain"]) if "grain" in e else e.get("canonical_key", "")
            out.append(f"- {name}: {e['description']} (grain: {grain})")
        out.append("")

        out.append("## Metrics")
        for name, m in s["metrics"].items():
            bits = [m["description"]]
            if m.get("directionality"):
                bits.append(f"**{m['directionality']}**")
            for k in ("filter", "ordering", "improved_means", "deteriorated_means"):
                if m.get(k):
                    bits.append(f"{k}: {m[k]}")
            if m.get("notes"):
                bits.append(str(m["notes"]).strip())
            if m.get("aggregation_rule"):
                bits.append(str(m["aggregation_rule"]).strip())
            out.append(f"- {name}: " + " | ".join(bits))
        out.append("")

        out.append("## Curated views (prefer these)")
        for name, desc in s.get("views", {}).items():
            out.append(f"- {name}: {desc}")
        out.append("")

        prov = s["provenance"]
        out.append(
            f"## Provenance\nEvery answer should cite {', '.join(prov['required_fields'])}. "
            f"source_system = {prov['source_system']}."
        )
        return "\n".join(out)

    def context(self, *, include_semantics: bool, include_schema: bool = True) -> str:
        parts = []
        if include_schema:
            parts.append(self.schema_block())
        if include_semantics:
            parts.append(self.semantics_block())
        return "\n\n".join(parts)


if __name__ == "__main__":
    sem = SemanticLayer.load()
    print(sem.context(include_semantics=True))
