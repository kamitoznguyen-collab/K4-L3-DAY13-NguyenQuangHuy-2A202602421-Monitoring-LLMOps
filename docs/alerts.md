# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ. Nguồn dữ liệu chuẩn là `data/logs.jsonl`; điều kiện chính thức nằm ở [`config/alert_rules.yaml`](../config/alert_rules.yaml).

Quy trình chung cho mọi alert: **Metrics → Logs → Traces**.

1. Mở dashboard (`python scripts/build_dashboard.py`) và xác định panel xấu cùng khoảng thời gian.
2. Lọc log trong khoảng đó, lấy `correlation_id` và `trace_id` của request bất thường:
   `python scripts/find_requests.py --slowest 5` hoặc `--failed`.
3. Mở trace trên Langfuse (project `day13-k4-l3a-<MSSV>`), so sánh span `retrieval` và `llm-generation` với trace bình thường.

## Alert 1

- Tên: `ChatLatencyP95High`
- Severity: P2
- Duration: 5m
- Kênh thông báo: Slack `#day13-k4-l3a-alerts`
- SLI/SLO liên quan: `fast_successful_requests` (request thành công với `latency_ms <= 3000`, mục tiêu 99.5%/28 ngày)
- Điều kiện và thời gian duy trì: P95 `latency_ms` của `response_sent` > 2000 ms liên tục 5 phút (cảnh báo sớm ở ~2/3 ngưỡng SLO 3000 ms; baseline P95 lúc warm ~160 ms)
- Ảnh hưởng tới người dùng: câu trả lời chậm; mỗi request quá 3 s tiêu thụ error budget
- Ba bước kiểm tra đầu tiên:
  1. Panel Latency: P95 tăng đơn lẻ hay cả P50? TTFT P95 có tăng không? (TTFT bình thường mà latency tăng → bước trước LLM chậm)
  2. `python scripts/find_requests.py --slowest 5`: lấy `correlation_id`/`trace_id`, xem có tập trung ở một `feature` không
  3. Mở trace: so sánh duration của span `retrieval` và `llm-generation`; khoảng trống trong root trước generation thường là prompt fetch
- Mitigation tạm thời: tắt nguồn chậm (`python scripts/inject_incident.py --scenario rag_slow --disable` trong lab); ở production: giảm top-k/timeout retrieval, bật cache, trả lời fallback không dùng context
- Owner: nguyenquanghuy

## Alert 2

- Tên: `ChatErrorRateHigh`
- Severity: P1
- Duration: 5m
- Kênh thông báo: Slack `#day13-k4-l3a-alerts`
- SLI/SLO liên quan: `fast_successful_requests`; guardrail `error_rate_pct_max: 2`, `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: `request_failed / request_received * 100` > 2% liên tục 5 phút
- Ảnh hưởng tới người dùng: nhận HTTP 500, không có câu trả lời; budget cháy nhanh nhất
- Ba bước kiểm tra đầu tiên:
  1. Panel Errors: xem `error_type` breakdown và retrieval success rate
  2. `python scripts/find_requests.py --failed`: đọc `error_type`, `tool_name`, `payload.detail` (đã scrub PII)
  3. Mở trace có cùng `trace_id`: observation nào có level `ERROR` và status message gì
- Mitigation tạm thời: tắt dependency lỗi (`--scenario tool_fail --disable` trong lab); ở production: circuit breaker cho retrieval, trả lời fallback thay vì 500, rollback deploy/prompt gần nhất
- Owner: nguyenquanghuy

## Alert 3

- Tên: `CostPerRequestSpike`
- Severity: P3
- Duration: 15m
- Kênh thông báo: Slack `#day13-k4-l3a-alerts`
- SLI/SLO liên quan: guardrail `daily_cost_usd_max: 2.5`; panel Cost và Tokens
- Điều kiện và thời gian duy trì: trung bình `cost_usd` mỗi `response_sent` > 0.004 USD (≈ 2× baseline) liên tục 15 phút
- Ảnh hưởng tới người dùng: không lỗi ngay nhưng đốt ngân sách; câu trả lời dài bất thường thường kém súc tích
- Ba bước kiểm tra đầu tiên:
  1. Panel Tokens: `tokens_out` hay `tokens_in` tăng? (out tăng → model trả lời dài; in tăng → prompt/context phình)
  2. `python scripts/find_requests.py --costliest 5`: xem `prompt_version`, `feature` của request đắt nhất
  3. Mở generation trong trace: `usage_details`, `cost_details` và prompt version được link
- Mitigation tạm thời: rollback prompt `production` (`python scripts/prompt_versions.py rollback`), đặt `max_tokens`, chuyển feature ít quan trọng sang model rẻ hơn; trong lab: `--scenario cost_spike --disable`
- Owner: nguyenquanghuy
