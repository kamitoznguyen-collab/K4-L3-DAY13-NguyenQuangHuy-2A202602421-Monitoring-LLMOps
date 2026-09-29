# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Quang Huy
- **MSSV:** 2A202602421
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/kamitoznguyen-collab/K4-L3-DAY13-NguyenQuangHuy-2A202602421-Monitoring-LLMOps
- **Commit SHA cuối:** `e53b27e5b5b06687533028edd1fe26e0f834ae61`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, seed 1311, 5 query, `latency_threshold_ms` 2000)
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602421`

## 2. Evidence index

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [`evidence/01-pytest.txt`](evidence/01-pytest.txt) |
| Log validator | [`evidence/02-log-validator.txt`](evidence/02-log-validator.txt) |
| Dashboard validator | [`evidence/03-dashboard-validator.txt`](evidence/03-dashboard-validator.txt) |
| Structured log | [`evidence/04-structured-log.txt`](evidence/04-structured-log.txt) |
| PII redaction | [`evidence/05-pii-redaction.txt`](evidence/05-pii-redaction.txt) |
| Trace list | [`evidence/06-trace-list.png`](evidence/06-trace-list.png) — project `day13-k4-l3a-2A202602421`, 217 root / 595 observations · số liệu API: [`evidence/raw/06-trace-summary.txt`](evidence/raw/06-trace-summary.txt) |
| Trace waterfall | [`evidence/07-trace-waterfall.png`](evidence/07-trace-waterfall.png) — trace `2516a638e164b47953430cb90663f179`: `lab-agent-run` → `retrieval` + `llm-generation` (0.15 s, 209 tokens, $0.002703) · cây span: [`evidence/raw/14-practice-traces.txt`](evidence/raw/14-practice-traces.txt) |
| Trace metadata | [`evidence/08-trace-metadata.png`](evidence/08-trace-metadata.png) — root `lab-agent-run` của trace incident `086ce802…`: `correlation_id=req-53697358` (khớp log), `prompt_name=day13-chat`, `prompt_label=production`, `prompt_version=1`, `prompt_source=langfuse`, model, feature; 145 tokens, $0.001755 |
| Prompt versions | [`evidence/09-prompt-versions.png`](evidence/09-prompt-versions.png) — v1 `production`+`baseline`, v2 `candidate`+`latest` · [`evidence/raw/09-prompt-versions.txt`](evidence/raw/09-prompt-versions.txt), [`evidence/raw/09-prompt-trace-ids.txt`](evidence/raw/09-prompt-trace-ids.txt) |
| Prompt rollback | [`evidence/10-prompt-rollback-before.png`](evidence/10-prompt-rollback-before.png) (sau promote: `production` → v2) · [`evidence/10-prompt-rollback-after.png`](evidence/10-prompt-rollback-after.png) (sau rollback: `production` → v1) · [`evidence/raw/10-prompt-promote.txt`](evidence/raw/10-prompt-promote.txt), [`evidence/raw/10-prompt-rollback.txt`](evidence/raw/10-prompt-rollback.txt) |
| Dashboard runtime | [`evidence/11-dashboard-overview.png`](evidence/11-dashboard-overview.png) (HTML gốc: [`evidence/11-dashboard.html`](evidence/11-dashboard.html)) |
| Incident metric | [`evidence/12-incident-metric.png`](evidence/12-incident-metric.png) (dashboard) · [`evidence/12-incident-metric.txt`](evidence/12-incident-metric.txt) (so sánh trước/trong incident) |
| Incident log | [`evidence/13-incident-log.txt`](evidence/13-incident-log.txt) · lệnh chạy: [`raw/20-challenge-run.txt`](evidence/raw/20-challenge-run.txt) |
| Incident trace | [`evidence/14-incident-trace.png`](evidence/14-incident-trace.png) — trace `086ce802f973e9cf2d8bb481f7f426d5`: root 2.65 s, **`retrieval` 2.50 s**, generation 0.15 s (TTFT 0.05 s, 145 tokens, $0.001755, prompt `day13-chat` v1) · so sánh với trace trước incident: [`evidence/14-incident-trace.txt`](evidence/14-incident-trace.txt) |
| Practice (3 scenario) | [`raw/12-practice-*.txt`](evidence/raw/), [`raw/14-practice-traces.txt`](evidence/raw/14-practice-traces.txt) |

Output baseline (trước khi sửa) nằm ở `evidence/raw/00-baseline-*.txt`.

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | **100/100** | Baseline: 40/43 dòng thiếu `correlation_id` (giá trị `MISSING`), 40 dòng thiếu enrichment, 0 correlation ID hợp lệ. PII đã "pass" sẵn chỉ vì `summarize_text` scrub `message_preview`; processor `scrub_event` thật sự chưa được đăng ký |
| `validate_dashboard.py` | 6/6 | **6/6** | Contract không đổi |
| `pytest` | 22 passed | **38 passed** | Thêm 16 test: correlation ID, enrichment, PII (CCCD/thẻ/hộ chiếu/nested), child observations, dashboard, alert rules, ghi log đồng thời |
| Số traces hợp lệ | 0 (chỉ root span, không có child) | **217 traces** (595 observations: 217 agent, 194 retriever, 184 generation) | 204/217 root có `correlation_id` dạng `req-…`; 13 trace còn lại tạo lúc chạy baseline, khi ID vẫn là `MISSING` |
| Số PII leak | Log: 0 (trên file log baseline) | **Log: 0 · Trace: 0** | Quét cả 5 pattern trên toàn bộ input/output/metadata của 595 observations; có 142 marker `[REDACTED_…]` |
| Latency P95 / TTFT P95 | P95 162 ms (server) nhưng client thấy ~780 ms / TTFT 50 ms | Lúc warm: P50 152 ms, P95 ~160 ms (P95 890 ms nếu tính cold start) / TTFT 50 ms | Client latency ở concurrency 5 giảm từ ~780 ms xuống ~170 ms sau khi sửa lỗi chặn event loop (xem mục 8) |
| Retrieval success rate | 100% | 95.2% trong cửa sổ 60 phút | Đã tính cả 10 request lỗi do practice `tool_fail`; ngoài incident là 100% |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` ([app/middleware.py](../app/middleware.py)) làm theo thứ tự:
  1. Gọi `clear_contextvars()` để không rò context từ request trước.
  2. Nhận header `x-request-id` nếu hợp lệ (`[A-Za-z0-9._-]{1,64}`, chống log injection); nếu không thì sinh `req-<8 hex>`.
  3. `bind_contextvars(correlation_id=…)`, lưu vào `request.state`.
  4. Trả lại hai header `x-request-id` và `x-response-time-ms`.
  
  ID được đưa vào metadata Langfuse qua `propagate_attributes`. `load_test.py` đọc ID từ header nên request lỗi 500 cũng có ID.
- **Các metadata được ghi vào structured log:**
  - Được bind trước `request_received` ([app/main.py](../app/main.py)): `user_id_hash` (SHA-256, 12 ký tự), `session_id`, `feature`, `model`, `env`.
  - Được agent bind thêm: `trace_id` (Langfuse), `prompt_version`, `prompt_source`.
  - Riêng `response_sent` có: `latency_ms`, `ttft_ms`, `tokens_in/out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
  
  Schema: [config/logging_schema.json](../config/logging_schema.json).
- **Cách bảo đảm PII được scrub trước khi ghi:** processor `scrub_event` đứng **trước** `JsonlFileProcessor` và `JSONRenderer` trong chuỗi processor ([app/logging_config.py](../app/logging_config.py)).
  - Scrub đệ quy mọi string (kể cả dict/list lồng nhau, ví dụ `payload.detail`).
  - Bỏ qua các field hệ thống `ts`, `level`, `correlation_id`, `user_id_hash`, để tránh trường hợp hash toàn chữ số bị nhận nhầm là CCCD.
  - Pattern trong [app/pii.py](../app/pii.py) gồm email, thẻ thanh toán, CCCD, điện thoại VN, hộ chiếu VN. Pattern thẻ chạy trước CCCD/điện thoại để số thẻ không bị cắt vụn.
  - Trace Langfuse chỉ nhận `scrub_text(prompt)` và `summarize_text(output)`; root span tắt `capture_input/output`.
- **Cách kiểm chứng kết quả:**
  - `validate_logs.py` đạt 100/100.
  - [`evidence/05-pii-redaction.txt`](evidence/05-pii-redaction.txt): 3 câu hỏi mẫu chứa email, điện thoại, số thẻ đều đã được redact; số lần PII mẫu xuất hiện nguyên văn trong `data/logs.jsonl` là 0.
  - Quét Langfuse bằng API: 0 match.
  - Có test `tests/test_correlation_id.py::test_logs_are_enriched_and_free_of_raw_pii`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** key trong `.env` là của project cá nhân. Mọi trace có tag `lab`, environment `dev`, và `correlation_id` khớp với dòng log trong `data/logs.jsonl` do chính máy tôi ghi. [`evidence/raw/06-trace-summary.txt`](evidence/raw/06-trace-summary.txt) được đọc qua API `GET /api/public/v2/observations` bằng key của project đó.
- **Cấu trúc root/retrieval/generation observations** ([app/agent.py](../app/agent.py)):

  ```text
  lab-agent-run   (agent, root)      metadata: correlation_id, feature, model, prompt_name/label/version/source, doc_count
  ├─ retrieval    (retriever)        input: query_preview đã scrub · output: doc_count · level ERROR nếu vector store lỗi
  └─ llm-generation (generation)     model, usage_details{input,output}, cost_details{input,output}, completion_start_time (TTFT), link prompt
  ```

  Ví dụ trace bình thường `ca723bd845753441999bccf9e1c4254f`: root 152 ms, retrieval 1 ms, generation 151 ms, 28 in / 124 out tokens, $0.001944.
- **Cách nối trace với log:** hai chiều.
  - Log → trace: mỗi dòng log API có `trace_id`. Lấy bằng `python scripts/find_requests.py --slowest 5` rồi mở `https://cloud.langfuse.com/project/<id>/traces/<trace_id>`.
  - Trace → log: metadata của trace có `correlation_id`; chạy `python scripts/find_requests.py --id <correlation_id>`.
- **Prompt name:** `day13-chat` (text prompt, giữ 3 biến `{{feature}}`, `{{docs}}`, `{{message}}`), quản lý bằng [scripts/prompt_versions.py](../scripts/prompt_versions.py).
- **Version/label baseline:** v1 — labels `baseline`, `production` (template mặc định của lab).
- **Version/label candidate:** v2 — label `candidate` (thêm dòng *"Answer in at most 3 short bullet points."*).
- **Trace ID của mỗi version** (cùng input *"How do I debug tail latency?"*; chi tiết trong [`evidence/raw/09-prompt-trace-ids.txt`](evidence/raw/09-prompt-trace-ids.txt)):

  | Bước | correlation_id | trace_id | label → version |
  |---|---|---|---|
  | baseline | `req-prompt8000` | `4a1ac073da2f97581a1a7f29ef914672` | production → v1 |
  | candidate | `req-prompt8001` | `c944f40ca5f1376e897fcca939436ea7` | candidate → v2 |
  | trước promote | `req-pv-v1` | `7fd398b6a02a96f3eb4c4ea5f8351086` | production → v1 |
  | sau promote | `req-pv-promoted` | `9dad2c4a71804262df06b111ae368944` | production → **v2** |
  | sau rollback | `req-pv-rolledback` | `18c18c3e30b4d27e225b7d259bcf500c` | production → **v1** |

  Generation của mỗi trace được link tới đúng prompt (`promptName=day13-chat`, `promptVersion` 1 hoặc 2).
- **Cách promote và rollback `production`:**
  - `python scripts/prompt_versions.py promote`: gọi `update_prompt(version=<candidate>, new_labels=["candidate","production"])`. Label là duy nhất nên `production` tự rời khỏi v1.
  - `python scripts/prompt_versions.py rollback`: làm ngược lại, đưa `production` về version có label `baseline`.
  - Không cần deploy lại code.
  
  **Lưu ý vận hành đã quan sát được:** app cache prompt 60 giây, và SDK dùng cơ chế stale-while-revalidate. Vì vậy request **đầu tiên** sau khi hết TTL vẫn nhận version cũ, rồi SDK mới refresh ở nền. Trong lần thử đầu, request `req-promoted` gửi ngay sau TTL vẫn là v1. Do đó thời gian để promote/rollback có hiệu lực là khoảng `TTL + 1 request`. Muốn rollback khẩn nhanh hơn thì phải giảm `cache_ttl_seconds` hoặc restart app.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** [scripts/build_dashboard.py](../scripts/build_dashboard.py) đọc `data/logs.jsonl` theo đúng contract [config/dashboard.yaml](../config/dashboard.yaml) và sinh một file HTML tự chứa. Cửa sổ 60 phút, auto-refresh 30 giây; mỗi panel có đơn vị, đường threshold nét đứt và badge OK/BREACH. Sáu panel:
  1. Latency P50/P95/P99 + TTFT P95.
  2. Traffic: count và request/phút.
  3. Error rate + breakdown `error_type` + retrieval success.
  4. Cost theo phút và cộng dồn.
  5. Tokens in/out.
  6. Quality mean.
  
  Ảnh runtime: [`evidence/11-dashboard-overview.png`](evidence/11-dashboard-overview.png). Ảnh có đủ baseline và 3 incident practice; panel Errors ở trạng thái BREACH (5.1% > 2%) vì `tool_fail`.
- **SLO và lý do chọn** ([config/slo.yaml](../config/slo.yaml)): SLI = `response_sent` có `latency_ms ≤ 3000` / `request_received`; mục tiêu **99.5% trong 28 ngày**.
  - Ngưỡng 3000 ms trùng với threshold của contract. Baseline P99 (kể cả cold start) chỉ khoảng 0.94 s, nên vẫn dư khoảng 3 lần cho độ trễ của LLM thật.
  - Chọn 99.5% chứ không phải 99.9% vì app phụ thuộc hai dịch vụ ngoài không có SLA (Langfuse prompt API, vector store).
- **Cách tính error budget:** budget = (1 − 0.995) × tổng request = **5 request "xấu" trên 1000 request** (lỗi hoặc chậm hơn 3 s).
  - Ví dụ ở mức 10 request/phút: 403,200 request / 28 ngày, tức được phép 2,016 request xấu.
  - Chính sách: nếu tiêu hơn 50% budget trong 7 ngày thì dừng rollout prompt/model mới; nếu hết budget thì chỉ deploy fix hoặc rollback.
  - Buổi practice `tool_fail` đã làm 10/195 request lỗi (5.1%), tức vượt 10 lần budget của cửa sổ đó.
- **Ba alert và runbook tương ứng** ([config/alert_rules.yaml](../config/alert_rules.yaml), [docs/alerts.md](../docs/alerts.md); tất cả đều symptom-based và báo về Slack `#day13-k4-l3a-alerts`):

  | Alert | Severity | Điều kiện | Duration | Practice kích hoạt |
  |---|---|---|---|---|
  | `ChatLatencyP95High` | P2 | P95 `latency_ms` > 2000 ms (cảnh báo sớm ở khoảng 2/3 ngưỡng SLO) | 5m | `rag_slow`: 2660 ms |
  | `ChatErrorRateHigh` | P1 | `request_failed / request_received` > 2% | 5m | `tool_fail`: 100% trong phút đó |
  | `CostPerRequestSpike` | P3 | trung bình `cost_usd` > $0.004 (khoảng 2 lần baseline $0.0019) | 15m | `cost_spike`: khoảng $0.010 mỗi request |

  Alert latency đặt ở 2000 ms thay vì 3000 ms. Lý do: `rag_slow` làm P95 tăng khoảng 17 lần (160 → 2660 ms) nhưng vẫn dưới 3000 ms, nên một alert đặt đúng ngưỡng SLO sẽ không bắn dù người dùng đã chịu độ trễ rõ rệt.

## 7. Điều tra challenge

Quy trình chạy (file challenge do Lab Coach gửi riêng, lưu ở `config/challenge.json`, đã gitignore và không commit):

```bash
python scripts/load_test.py --challenge --concurrency 5     # baseline cùng input, chưa inject (10:10:19Z)
python scripts/inject_incident.py                            # đọc incident từ challenge.json (10:11:25Z)
python scripts/load_test.py --challenge --concurrency 5
python scripts/build_dashboard.py                            # Metrics
python scripts/find_requests.py --slowest 5 --minutes 5      # Logs
# mở trace_id trên Langfuse                                   # Traces
python scripts/inject_incident.py --disable                  # Fix (10:12:39Z), rồi chạy lại để xác nhận
```

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`. File gồm cohort K4, seed 1311, 5 query cùng feature `monitoring`, và `latency_threshold_ms = 2000`.
- **Khoảng thời gian điều tra (UTC, 2026-09-29):**
  - Baseline cùng input: 10:10:19.
  - Incident: 10:11:25–10:11:29.
  - Fix và xác nhận hồi phục: 10:12:39.
- **Triệu chứng từ metrics** ([dashboard](evidence/12-incident-metric.png), [số liệu](evidence/12-incident-metric.txt)): so sánh cùng 5 query trước và trong incident.

  | Metric | Trước | Trong incident |
  |---|---|---|
  | Latency P50 / P95 / P99 | 152 / 153 / 153 ms | **2653 / 2654 / 2654 ms** (~17×) |
  | Request vượt `latency_threshold_ms` 2000 | 0/5 | **5/5** |
  | TTFT P95 | 50 ms | 50 ms (không đổi) |
  | Error rate / retrieval success | 0% / 5/5 | 0% / 5/5 (không đổi) |
  | tokens_out trung bình / cost trung bình | 114 / $0.00181 | 115 / $0.00183 (không đổi) |

  Kết luận từ metrics: đây là sự cố **chỉ về latency**. Error và cost không đổi, nên loại trừ lỗi dependency và loại trừ việc model sinh nhiều token hơn. TTFT không đổi, nên khoảng thời gian bị chậm nằm **trước** lúc LLM bắt đầu sinh token. Dashboard 60 phút cho P95 = 2654 ms, vẫn dưới ngưỡng SLO 3000 ms nhưng vượt ngưỡng 2000 ms của challenge và của alert `ChatLatencyP95High`. Đây chính là lý do tôi đặt alert ở 2000 ms.
- **Log line và correlation ID liên quan** ([log](evidence/13-incident-log.txt)): cả 5 request `feature=monitoring` trong khoảng 10:11:26–10:11:29 đều chậm như nhau. Ví dụ:

  ```text
  correlation_id=req-53697358 | trace_id=086ce802f973e9cf2d8bb481f7f426d5 | feature=monitoring | prompt_version=1
  | latency_ms=2652 | ttft_ms=50 | tokens_out=110 | cost_usd=0.001755 | tool_success=True
  ```

  Log cho thấy prompt version không đổi (v1) và `tool_success=True`, tức retrieval không lỗi, chỉ chậm.
- **Trace ID và span gây ảnh hưởng** ([cây span](evidence/14-incident-trace.txt)):

  | Trace | root `lab-agent-run` | `retrieval` | `llm-generation` |
  |---|---|---|---|
  | trước incident `af07f7dc1c5cd84c363b1136955b605d` (`req-15760395`) | 154 ms | **0 ms** | 152 ms, 36/107 tokens |
  | incident `086ce802f973e9cf2d8bb481f7f426d5` (`req-53697358`) | 2653 ms | **2501 ms** | 151 ms, 35/110 tokens |
  | incident `17fece7a1100cefb45a89cfbe9eb153f` (`req-f7438fd4`) | 2654 ms | **2502 ms** | 152 ms, 35/116 tokens |

  Span **`retrieval`** chiếm khoảng 94% thời gian của trace; generation, model và prompt (`day13-chat` v1, production) giống hệt trước incident.
- **Root cause:** bước retrieval (vector store) chậm thêm khoảng 2.5 s cho mỗi request. Incident được inject là `rag_slow`, khớp với cả ba lớp evidence:
  - Metric: latency tăng, TTFT/error/cost không đổi.
  - Log: `tool_success=True`, prompt không đổi.
  - Trace: span `retrieval` từ 0 lên 2501 ms.
- **Fix action:** `python scripts/inject_incident.py --disable` lúc 10:12:39, tức gỡ nguồn gây chậm ở retrieval. Chạy lại cùng 5 query cho latency client 168–181 ms, tất cả 200 OK ([recovery](evidence/raw/20-challenge-recovery.txt)). Nếu là production, hướng mitigation là:
  - Đặt timeout cho retrieval (ví dụ 800 ms) và fallback sang câu trả lời không có context, hoặc dùng cache kết quả retrieval cho câu hỏi lặp lại.
  - Scale hoặc chuyển sang replica khác của vector store.
- **Preventive measure:**
  1. Alert `ChatLatencyP95High` (P95 > 2000 ms trong 5 phút) sẽ bắn ở sự cố này. Nên thêm alert theo từng span, cho duration của `retrieval` P95 > 500 ms, để chỉ thẳng vào thành phần lỗi.
  2. Retrieval có timeout và circuit breaker, để một dependency chậm không kéo cả request vượt SLO.
  3. Tách panel latency theo `feature`, vì sự cố chỉ ảnh hưởng `monitoring` trong workload challenge.
  4. Giữ span `retrieval` riêng trong trace và `trace_id` trong log. Nhờ vậy lần này đi từ metric đến root cause chỉ mất 3 lệnh.

**Practice trước challenge** (đã chạy cả 3 scenario theo cùng quy trình; chi tiết ở [`raw/12-practice-*.txt`](evidence/raw/) và [`raw/14-practice-traces.txt`](evidence/raw/14-practice-traces.txt)):

| Scenario | Metric | Log | Trace |
|---|---|---|---|
| `rag_slow` | P95 160 → 2660 ms | `req-f49a8bd2`, `latency_ms=2660` | `fcba55e0…`: `retrieval` 2506 ms |
| `tool_fail` | error rate 0 → 100% trong phút đó | `req-abcca514`, `request_failed`, `RuntimeError` | `9a061ef7…`: `retrieval` level ERROR, *"Vector store timeout"* |
| `cost_spike` | cost ~$0.0019 → ~$0.010 mỗi request | `req-77e9d989`, `tokens_out=688` | `e4306976…`: `llm-generation` output 688 tokens, prompt v1 không đổi |

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** tôi ghi `trace_id` của Langfuse vào **mọi** dòng log. Giá trị này được bind vào contextvars ngay đầu `LabAgent.run`, nên cả `request_failed` cũng có. Nhờ vậy bước Logs → Traces chỉ là copy một ID thay vì lọc Langfuse theo metadata và khoảng thời gian. Tương tự, tôi log `prompt_version` để biết request nào dùng prompt nào mà không cần mở trace. Instrumentation dùng `@observe(as_type="retriever"|"generation")` trên hai method riêng thay vì `start_as_current_observation`, để giữ được test sẵn có (client giả không có method đó) và code ngắn hơn.
- **Một lỗi/blocker đã gặp:** khi chạy `load_test.py --concurrency 5`, server ghi `latency_ms` P95 = 162 ms nhưng client đo được khoảng 780 ms. Header `x-response-time-ms` của các request đồng thời tăng dần theo bậc 156 → 312 → 466 → 622 → 782 ms, nghĩa là server đang xử lý **tuần tự**.
- **Cách tìm nguyên nhân và xử lý:**
  - `/chat` được khai báo là `async def` nhưng gọi `agent.run` đồng bộ (có `time.sleep`), nên chặn event loop.
  - Tôi xác nhận bằng cách chạy 5 request đồng thời in-process (khoảng 170 ms mỗi request, song song), rồi so với server thật.
  - Fix: đổi handler thành `def` để FastAPI chạy trong threadpool. Client latency còn khoảng 170 ms ([trước](evidence/raw/15-before-threadpool-fix-load-c5.txt) / [sau](evidence/raw/11-baseline-load-c5.txt)).
  - Bài học: `latency_ms` đo trong agent **không thấy** thời gian xếp hàng. Cần so với `x-response-time-ms`, hoặc latency phía client, để phát hiện nghẽn ở tầng server.
  - Ghi chú thêm: request đầu tiên sau khi start mất 0.9–5.9 s do fetch prompt Langfuse lúc cache còn lạnh. Đó là nguồn của các điểm P99 cao trên panel latency.
- **Lỗi thứ hai, phát hiện nhờ challenge:** fix threadpool ở trên gây ra một lỗi mới.
  - Triệu chứng: khi tính metric challenge, mỗi lượt 5 request chỉ có 4 dòng `request_received`.
  - Nguyên nhân: nhiều thread cùng append vào `data/logs.jsonl`, các dòng JSON bị đan xen vào nhau (11/449 dòng hỏng).
  - Vì sao không ai thấy: `validate_logs.py` lặng lẽ bỏ qua dòng không parse được, nên vẫn báo 100/100.
  - Fix: thêm `threading.Lock` quanh thao tác ghi file trong `JsonlFileProcessor`, kèm test 400 lần ghi từ 16 thread. Test này fail trước khi sửa và pass sau khi sửa.
  - Sau đó tôi cất log cũ sang file khác và chạy lại toàn bộ challenge trên log sạch (0 dòng hỏng).
  - Bài học: một thay đổi về concurrency phải được kiểm tra trên *toàn bộ* pipeline telemetry, không chỉ trên latency.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics** trả lời "có vấn đề gì, từ lúc nào, nặng cỡ nào", dựa trên tổng hợp của nhiều request (P95, error rate, cost). Ví dụ: P95 nhảy từ 160 lên 2660 ms lúc 08:32.
  - **Logs** trả lời "request nào bị ảnh hưởng": lọc đúng khoảng thời gian đó để lấy `correlation_id` và `trace_id` cụ thể, kèm context (feature, prompt_version, error_type).
  - **Traces** trả lời "bước nào gây ra": waterfall của đúng request đó cho thấy `retrieval` chiếm 2506/2661 ms.
  - Chỉ kết luận khi cả ba lớp cùng chỉ về một nguyên nhân. Ví dụ ở `cost_spike`, metric cost tăng, log có `tokens_out` 688, và trace cho thấy output của generation tăng trong khi prompt/input không đổi.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Prompt là "code" thay đổi ngoài quy trình deploy. Nếu không gắn version vào trace và log thì không trả lời được câu hỏi "chất lượng/chi phí thay đổi vì prompt mới hay vì model/dữ liệu".
  - Label `production` cho phép promote/rollback trong vài giây mà không cần redeploy, nhưng phải tính tới TTL của cache.
  - Token và cost là chỉ số "lỗi thầm lặng": `cost_spike` không làm latency hay error thay đổi, chỉ lộ ra qua panel cost/tokens.
  - SLO và error budget biến "hệ thống có ổn không" thành một con số dùng để quyết định dừng rollout hay không.
- **Điều quan trọng nhất đã học:** observability phải được thiết kế để *nối* được các lớp với nhau (`correlation_id` ↔ `trace_id` ↔ `prompt_version`), chứ không chỉ để *thu thập*. Ngoài ra, một metric đo sai chỗ (latency trong agent, không tính thời gian xếp hàng) có thể che mất sự cố thật.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  - Ảnh dashboard `11-dashboard-overview.png` được tạo từ log trước khi sửa lỗi ghi đồng thời, nên có thể thiếu vài dòng log bị hỏng. Log đó được giữ lại ở `data/logs.pre-lockfix.jsonl` (gitignore).
  - Dashboard là HTML sinh từ log, chưa phải công cụ realtime như Grafana; chế độ `--watch` build lại mỗi 30 giây.
  - `quality_score` vẫn là heuristic của starter.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
