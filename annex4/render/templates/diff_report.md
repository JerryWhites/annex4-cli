# Annex IV Change Impact Report

**Old version:** {{ report.old_version or "—" }}
**New version:** {{ report.new_version or "—" }}

{% if report.regulation_version_changed %}
> ⚠ **Regulation version changed between these dossiers.** Some differences may reflect
> regulatory updates rather than system changes. Review with legal counsel before filing.
{% endif %}

---

{% if not report.entries %}
No changes detected between the two dossiers.
{% else %}

## Changes by Annex IV section

{% set sections = {} %}
{% for entry in report.entries %}
  {% if entry.section_name not in sections %}
    {% set _ = sections.update({entry.section_name: []}) %}
  {% endif %}
  {% set _ = sections[entry.section_name].append(entry) %}
{% endfor %}

{% for section_name, section_entries in sections.items() %}
### Section {{ section_entries[0].annex_iv_section }} — {{ section_name }}

*Citations: {{ section_entries[0].citations | join(", ") }}*

| Field | Change | Substantiality | Old value | New value |
|-------|--------|----------------|-----------|-----------|
{% for entry in section_entries %}| `{{ entry.path }}` | {{ entry.kind }} | **{{ entry.substantiality }}** | {{ entry.old_value if entry.old_value is not none else "—" }} | {{ entry.new_value if entry.new_value is not none else "—" }} |
{% endfor %}

{% endfor %}

---

## Factors that may indicate substantial modification (Article 43(4))

The following checklist identifies areas of change that regulators and notified bodies
consider when assessing whether a modification is substantial. A checked item does **not**
constitute a legal determination of substantiality.

{% for f in report.substantiality_factors %}
- [{{ "x" if f.triggered else " " }}] **{{ f.id }}.** {{ f.factor }}
  *({{ f.articles | join(", ") }})*{% if f.triggered %} — **changes detected in this area**{% endif %}

{% endfor %}

{% endif %}

---

> **{{ report.LEGAL_NOTICE }}**
