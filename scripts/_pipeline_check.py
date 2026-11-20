"""Quick pipeline verification through the full collector path."""
import sys; sys.path.insert(0, '.')
from collector.sources.psutil_source import collect_metrics
from collector.sources.security_source import collect_security_signals
from collector.pipeline.normalizer import normalize_metrics
from collector.pipeline.redactor import redact_event
from collector.pipeline.allowlist import apply_allowlist

# Replicate exactly what collector.py does
raw_infra = collect_metrics()
raw_security = collect_security_signals()

infra_data_source = raw_infra.get("data_source", "live")
raw_infra.update(raw_security)
raw_infra["data_source"] = infra_data_source
raw_infra["_security_data_source"] = raw_security.get("data_source", "live")

events = normalize_metrics(raw_infra, collector_id='test-collector')
print(f"Events generated: {len(events)}")
for ev in events:
    redacted = redact_event(ev)
    approved = apply_allowlist(redacted)
    cat = approved["metric_category"]
    val = approved["metric_value"]
    ds = approved.get("data_source", "MISSING")
    print(f"  {cat:10s} {val:7.2f}  data_source={ds}")
    assert "raw_config_snippet" not in approved
    assert "_raw_usernames" not in approved
    assert "hostname" not in approved

print("\nAll checks passed!")
print("\nExpected: cpu/memory/disk/network -> 'live', security -> depends on wevtutil")
