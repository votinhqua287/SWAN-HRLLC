# Đánh giá tính khả thi: "Tail-Latency-Aware SWAN for HRLLC under Bursty Traffic" nộp IEEE TWC

*Ngày đánh giá: 25/09/2026. Người đánh giá: Claude (trợ lý nghiên cứu), theo yêu cầu của tác giả chính.*

> **Cập nhật (sau khi nhận file guide).** File guide đã được đưa vào repo và đối chiếu (mục 9). Khung nghiên cứu, mã
> nguồn và bản nháp đã được điều chỉnh theo guide: mô hình kích hoạt segment với năng lượng mạch và trễ cấu hình (H2),
> mục tiêu năng lượng + chi phí cấu hình, đủ 8 baseline bắt buộc, các hình bắt buộc (mean delay vs tail, chọn chế độ theo
> hàng đợi, năng lượng vs mục tiêu, Poisson vs bursty), ablation, kịch bản một thiết bị với xấp xỉ đuôi Route A, unit tests
> và cấu trúc mã `src/…`. Guide ưu tiên TCOM (TWC là phương án thay thế); bản nháp hiện định dạng TWC, đổi sang TCOM chỉ cần
> sửa dòng `\markboth`.
>
> **Lưu ý về nguồn dữ liệu ban đầu.** File hướng dẫn gốc
> `D:\Research\SWAN-PASS-HRLLC\02_Tail_Latency_Aware_SWAN_HRLLC_Bursty_Traffic.md` nằm trên máy Windows
> của bạn và **không được đính kèm** vào phiên làm việc từ xa này (repository trên GitHub trống hoàn toàn).
> Toàn bộ khung nghiên cứu dưới đây được tôi tái dựng từ **tiêu đề** của guide (tail-latency-aware, SWAN, HRLLC,
> bursty traffic), tên thư mục (SWAN-PASS-HRLLC) và một khảo sát tài liệu độc lập (3 agent, ~470 truy vấn)
> tính đến ngày 25/09/2026. Khi bạn đưa file guide vào repo, cần đối chiếu lại các giả định ở mục 4.
> Ngoài ra, trong môi trường này chỉ đọc được **tóm tắt tìm kiếm** (arXiv/IEEE Xplore bị chặn), nên mọi trích dẫn
> được đánh dấu *[verify]* cần kiểm tra lại với bản PDF trước khi nộp.

## 1. Kết luận ngắn

**Khả thi, và có cơ sở tốt để nhắm tới TWC**, với hai điều kiện:

1. Phần lý thuyết do đồng nghiệp đảm nhiệm phải cho ra **ít nhất 3 kết quả đóng** (Lemma/Proposition/Theorem)
   gắn với thuật toán (xem mục 6). TWC hiếm khi nhận bài "mô hình + heuristic + mô phỏng" thuần túy.
2. Mô phỏng phải chứng minh được xác suất vi phạm trễ ở mức HRLLC ($10^{-4}$–$10^{-6}$) với khoảng tin cậy hợp lý,
   và so sánh với các bộ lập lịch kinh điển nhạy-đuôi (M-LWDF, EXP rule, EDF) chứ không chỉ với round-robin.
   Khung mô phỏng trong repo này đã làm được điều đó (mục 5).

## 2. Tính mới (novelty) — bằng chứng từ khảo sát tài liệu

Khảo sát các feed arXiv eess.SP / cs.IT / cs.NI (03/2024 → 25/09/2026) và IEEE Xplore cho thấy:

| Chiều nghiên cứu | Đã có trong PASS/SWAN? | Bài gần nhất |
|---|---|---|
| Finite blocklength (FBL) trong PASS | Có, nhưng **1 user, full-buffer, 1 ống dẫn sóng dài** | Lin et al., arXiv:2509.01222 (URLLC rate opt.); Pan et al., *Entropy* 28(7):722, 2026 (statistical CSI, short packet) |
| Hàng đợi / xác suất vi phạm trễ / effective capacity / SNC | **Chưa có bài nào** | Chỉ có bài tầm nhìn Xu et al., arXiv:2609.17332 nêu "queue-aware PA scheduling" là bài toán mở |
| Lưu lượng bursty (ON–OFF / MMPP) tại BS-PASS | **Chưa có** | "Traffic" trong PASS chỉ là tải offloading (Ding–Schober–Poor, arXiv:2606.03253) hoặc tải random access (Shan et al., arXiv:2606.04913) |
| Đa người dùng + FBL trong SWAN | **Chưa có** | SWAN đa người dùng chỉ có sum-rate/ISAC/random-access (Gu et al. WCL 2026; Jiang et al.; Shan et al.) |
| Trễ cấu hình lại anten (reconfiguration delay) | Có cho PASS 1 ống (Wang–So–Ding, arXiv:2608.10136, 2607.23595), FAS (Zhu et al., arXiv:2605.06275) — **chưa kết hợp với hàng đợi** | |
| Metric thời gian trên SWAN | Chỉ có AoI (Zheng–Cotton–Duong, IEEE TCCN 2026) | |

=> Một bài "downlink multi-user SWAN × FBL × hàng đợi/tail latency × bursty traffic × lập lịch/aggregation × trễ cấu hình lại"
là **bài đầu tiên** đồng thời ở cả các chiều trên. Đây là điểm bán hàng chính cho TWC.

## 3. Mức độ phù hợp với TWC

- **Phạm vi:** TWC ưu tiên (i) mô hình hệ thống mới có động cơ vật lý, (ii) thuật toán có phân tích, (iii) mô phỏng sâu.
  Bài này đáp ứng (i) qua SWAN (ống dẫn sóng phân đoạn, mỗi đoạn một feed/RF chain, một PA kích hoạt mỗi đoạn — không có
  inter-antenna radiation), (ii) qua khung hai thang thời gian (đặt PA theo thống kê đuôi + lập lịch theo giá trị gói), (iii) qua
  khung mô phỏng cấp slot với FBL, hàng đợi có deadline và nguồn ON–OFF.
- **Độ dài:** TWC giới hạn **13 trang** cho bản nộp đầu (bản nháp hiện tại: 12 trang kể cả tài liệu tham khảo, Abstract 215 từ; phần chứng minh của đồng nghiệp cần được viết gọn trong Appendix hoặc chuyển thành supplementary material). Quy tắc ngân sách trang được ghi trong `.claude/skills/ieee-paper-writing/SKILL.md`.
- **Điểm yếu cần bù:** phần lý thuyết. Các "[To do]" trong bản nháp là chỗ đồng nghiệp cần điền (mục 6).

## 4. Các giả định thiết kế tôi đã chọn (cần đối chiếu với guide của bạn)

1. **Hướng truyền:** downlink (BS → K user HRLLC), vì gói điều khiển công nghiệp/XR chủ yếu chiều xuống và TWC-đã có SWAN uplink.
2. **Kiến trúc SWAN:** $M$ đoạn dài $L_s$ nối tiếp trên trục $x$ ở độ cao $d$; feed ở đầu trái mỗi đoạn (theo Ouyang et al., TCOM 2026);
   **một PA kích hoạt mỗi đoạn**; mỗi đoạn có RF chain riêng ⇒ tiền mã hóa số qua các đoạn (chế độ segment multiplexing, SM) hoặc
   kết hợp đồng pha toàn bộ đoạn cho một user (segment aggregation, SA). Ràng buộc công suất **theo từng feed** $P_{\max}$.
3. **Kênh:** LoS dominant theo mô hình PASS chuẩn ($\sqrt{\eta}/r$, pha trong ống $2\pi n_{\rm eff}\ell/\lambda$, suy hao $e^{-\alpha\ell}$,
   $\kappa = 0.08$ dB/m). Có tùy chọn Rician để thử độ bền vững.
4. **Truyền dẫn:** slot $T_s = 0.1$ ms, $n = 200$ channel uses (B = 2 MHz), gói 32 byte, mã FBL với xấp xỉ normal (Polyanskiy).
   Lỗi giải mã ⇒ gói ở lại hàng đợi (ARQ), gói quá hạn $D_{\max}$ bị loại (deadline-dropping, đúng ngữ nghĩa HRLLC).
5. **Lưu lượng bursty:** nguồn ON–OFF Markov (IPP) với đỉnh $h$ gói/slot, thời gian ON/OFF trung bình $1/\alpha$, $1/\beta$;
   có lớp user "critical" (đỉnh cao hơn, $\delta$ chặt hơn) để thể hiện tính "tail-aware" của việc đặt PA.
6. **Metric đuôi:** $\Pr\{D_k > D_{\max}\} \le \delta_k$ với $D_{\max} \in [0.3, 3]$ ms, $\delta_k \in [10^{-6}, 10^{-3}]$.
7. **Trễ cấu hình lại PA:** $\tau_r$ (slot) mỗi lần đổi vị trí kích hoạt của một đoạn (đoạn im lặng trong $\tau_r$);
   scheme đề xuất chỉ đổi vị trí ở cấp khung (frame) nên gần như không tốn, benchmark "reactive repositioning" trả giá mỗi slot.

## 5. Khung mô phỏng đã có (thư mục `sim/`)

- `swan.py` – hình học SWAN, kênh, ZF equal-SNR với ràng buộc công suất từng đoạn, EGT cho chế độ aggregation, bảng SNR cho mọi tập user.
- `fbl.py` – xấp xỉ normal FBL (rate, xác suất lỗi, số gói tối ưu).
- `traffic.py` – nguồn ON–OFF/Poisson/periodic+jitter; công thức tốc độ yêu cầu $c_{\rm req}$ dạng đóng.
- `placement.py` – TAPP (tail-aware placement, BCD), sum-rate, max-min, nearest, center.
- `scheduler.py` – bộ lập lịch theo giá trị gói (đề xuất), max-weight, M-LWDF, EDF, RR, PF.
- `simulator.py` – vòng lặp cấp slot, hàng đợi vòng theo tuổi gói, thống kê CCDF trễ; `experiments.py` – các thí nghiệm & hình.

Tốc độ ≈ 110 µs/slot ⇒ $10^6$ slot/100 s/lõi; đủ để ước lượng xác suất $10^{-5}$ với 4 lõi.

## 6. Phân công: bạn (thuật toán, mô phỏng) – đồng nghiệp (chứng minh)

Các mục **[To do]** trong `paper/main.tex` (chi tiết trong `docs/math_todo_for_colleague.md`):

| # | Kết quả cần chứng minh | Vai trò trong bài | Kỹ thuật gợi ý |
|---|---|---|---|
| L1 | $c_{\rm req} = h(\beta+\Lambda)/(\alpha+\beta+\Lambda)$, $\Lambda=\ln(1/\delta)/D_{\max}$ | Ánh xạ ràng buộc đuôi → tốc độ phục vụ yêu cầu (dùng ở cả hai thang thời gian) | Effective bandwidth của nguồn Markov fluid (Anick–Mitra–Sondhi; Kelly) + large-buffer asymptotics |
| L2 | Vị trí PA tối ưu dạng đóng khi một đoạn phục vụ chủ yếu một/hai user | Khởi tạo & lời giải 1-D của BCD | Đạo hàm của $1/r^2$ theo $x_m$, phương trình bậc hai |
| P1 | BCD (Algorithm 1) đơn điệu, hội tụ về điểm dừng; độ phức tạp | Tính hợp lệ của TAPP | Chuỗi đơn điệu bị chặn |
| T1 | Cận trên xác suất vi phạm trễ của user $k$ dưới TLA-SWAN (EC/SNC với dịch vụ FBL) | Định lý chính về hiệu năng | Effective capacity với FBL (Gursoy 2013; Schiessl 2018) hoặc (min,×) SNC |
| T2 | Cận drift-plus-penalty: công suất trung bình $\le$ tối ưu $+ O(1/V)$, hàng đợi ảo bị chặn ⇒ cận trễ xấu nhất | Bảo đảm của Algorithm 2 | Neely 2010/2013 (ε-persistent queue) |
| T3 (tùy chọn) | Điều kiện đủ để đặt PA theo thống kê (khung) không thua reactive repositioning khi $\tau_r$ vượt ngưỡng | Giải thích Fig. về $\tau_r$ | So sánh throughput hiệu dụng $(1-\tau_r/T)R$ |

## 7. Rủi ro và cách xử lý

| Rủi ro | Mức | Cách xử lý trong bản nháp |
|---|---|---|
| Reviewer nghi ngờ PA có thể đổi vị trí theo slot | Cao | Thiết kế **hai thang thời gian**; PA chỉ đổi ở cấp khung; benchmark reactive có $\tau_r$; trích dẫn tutorial PASS về thời gian kích hoạt (µs–ms rời rạc, ms–s trượt liên tục) *[verify]* |
| Bộ lập lịch bị coi là heuristic | Trung bình | Bộ lập lịch được suy từ drift-plus-penalty với hàng đợi ảo tín dụng đuôi + giá trị gói theo hàm mũ (liên hệ EXP rule/LWDF có tính tối ưu độ lệch lớn); T2 do đồng nghiệp chứng minh |
| Ước lượng $10^{-5}$–$10^{-6}$ bằng mô phỏng | Trung bình | Chạy $10^6$–$10^7$ slot, gộp nhiều lần thả user; báo cáo số vi phạm tuyệt đối |
| Kênh LoS thuần | Thấp | Thí nghiệm Rician $K$-factor; câu chữ "LoS-dominant, as in the PASS literature" |
| Số RF chain = số đoạn | Thấp | Dùng $M = 4$–$8$; nêu HSSM (Gao et al.) làm hướng mở |
| Tài liệu trích dẫn chưa đối chiếu PDF | Trung bình | Các entry có ghi chú `% TODO verify` trong `refs.bib` |

## 8. Lộ trình đề xuất

1. Tuần 1–2: bạn đối chiếu guide gốc với `docs/research_design.md`, chốt tham số; chạy lại toàn bộ `sim/experiments.py` với số slot lớn.
2. Tuần 2–4: đồng nghiệp hoàn thiện L1, L2, P1, T1, T2 (thứ tự ưu tiên: L1 → T2 → T1 → P1 → L2).
3. Tuần 4–5: ghép phần toán vào `paper/main.tex`, cập nhật hình với cận lý thuyết (Fig. so sánh cận T1 với mô phỏng).
4. Tuần 6: rà soát, kiểm tra trích dẫn, nộp TWC.

## 9. Đối chiếu với file guide (02_Tail_Latency_Aware_SWAN_HRLLC_Bursty_Traffic.md)

| Mục guide | Trạng thái | Ghi chú |
|---|---|---|
| §2 câu hỏi nghiên cứu (chọn mode, active segments, power, service) | Đã có | Action $a_t=(\mathcal S,\mathcal A,\mathbf b,\rho)$ trong `src/service.py` + `src/controller.py` |
| §3 H1–H4 | Có thí nghiệm tương ứng | `key` (H1), `energy`/`target`/`cfg`/`modes` (H2), toàn bộ so sánh (H3), `fixedj` + `ablation` (H4) |
| §4 kiến trúc: 1 thiết bị trước, 2 lớp sau; SS/SA, SM nếu mô hình hóa RF chain | Đã có | `single` (K=1), `hetero` (2 lớp); SM có tính năng lượng mạch mỗi RF chain |
| §5 lưu lượng Markov ON–OFF, Bernoulli/Poisson để kiểm chứng | Đã có | `src/arrivals.py`; self-similar chưa làm (tùy chọn) |
| §6 hàng đợi, trễ = D_q + D_cfg + D_tx + D_proc | Đã có (D_proc = 0) | `src/queue.py`, `src/simulator.py` |
| §7 mô hình dịch vụ SWAN có suy hao ống, không gian tự do, SNR theo segment, overhead cấu hình | Đã có | `src/swan_channel.py`, `src/service.py` |
| §8 FBL | Đã có | `src/fbl.py` (có ablation Shannon) |
| §9 metric đuôi: P(D>Dmax), p99…p99.999, CVaR, mean chỉ phụ | Đã có | `experiments/run_campaign.py::load`, `src/tail_analysis.py` |
| §10 route phân tích A/B/C | Route A số học đã có; chứng minh do đồng nghiệp | `src/tail_analysis.py`; Lemma 1, Theorem 2 [To do] |
| §11 bài toán tối ưu năng lượng + cấu hình s.t. đuôi | Đã có | (P1) trong bài |
| §12 controller Stage A–D | Đã có | bảng hành động offline (A), trạng thái hàng đợi/kênh/mode (B), điểm rủi ro = thế năng đuôi (C), drift-plus-penalty (D); DRL (E) không làm |
| §13 8 baseline | Đủ | conventional PASS, fixed SS, fixed SA, full activation, rate-max, MW (avg-delay), MW+V (queue-aware non-tail), proposed |
| §14 tham số | Trong khoảng khuyến nghị | M 2–10, 32 byte, slot 0.1 ms, deadline 0.3–3 ms, mục tiêu 1e-3–1e-7 |
| §15–16 hình bắt buộc | Có 10/10 | xem `experiments/plots.py` |
| §17 ablation | Có | Bernoulli/bursty, không trễ cấu hình, Shannon/FBL, không suy hao ống, mode cố định, queue-blind, tail-aware vs average-aware |
| §18 cấu trúc mã | Theo guide | `src/`, `experiments/`, `tests/`, `results/`, `paper/figures/` |
| §19 unit tests | 9 test, pass | `tests/test_basic.py` |
| §21 GO/NO-GO | Đánh giá sau khi có kết quả campaign | xem mục "Kết quả" trong bài |

## 10. Kết quả chính của campaign mô phỏng (đánh giá GO/NO-GO theo §21 của guide)

Tham số mặc định: $M=4$, $K=8$, $P_{\max}=-10$ dBm, ON–OFF đỉnh $h=3$ gói/slot, burst 1 ms, activity 0.1, $D_{\max}=1$ ms.

| Tiêu chí GO/NO-GO | Bằng chứng | Kết luận |
|---|---|---|
| Burstiness thay đổi chính sách tối ưu | Poisson cùng tải trung bình: 0 vi phạm cho mọi controller (1.1M gói); ON–OFF: $5\times10^{-3}$ (MW), $1.2\times10^{-3}$ (TLA). Độ sâu gộp tối ưu: $j=2$ với Poisson, $j=M$ với ON–OFF (Fig. fixedj) | **GO** |
| Cải thiện đuôi, không chỉ trễ trung bình | Fig. key: tại $h=2$ trễ trung bình bằng nhau (0.11 ms) nhưng $P(D>1\,\text{ms})$: TLA 0 vs MW $1.1\times10^{-4}$, rate-max $1.7\times10^{-4}$; CCDF: TLA $2.7\times10^{-3}$ vs MW $7.1\times10^{-3}$ vs sum-rate $1.3\times10^{-2}$ | **GO** |
| Overhead cấu hình tạo trade-off SWAN thật | Năng lượng: cùng đuôi $4.4\times10^{-3}$, TLA cần 94 mW vs MW 138 mW; trễ kích hoạt $\tau_{\rm cfg}$ 0→4 slot làm đuôi tăng $2.5\times10^{-3}\to8\times10^{-2}$; reactive repositioning tệ hơn TAPP ngay cả khi $\tau_r=0$ và giảm 30× tại $\tau_r=1$ ms | **GO** |
| Biểu thức đuôi giải tích khớp mô phỏng | Một thiết bị, SA cố định: xấp xỉ EB/EC khớp mô phỏng trong hệ số ≤2.5 trên 4 bậc độ lớn (Fig. single) | **GO** (chứng minh: đồng nghiệp) |
| Lợi ích bền qua nhiều tải/burst | TLA tốt hơn MW 2.4–50× trên $K=4..12$, 1.5–500× trên burst 4→0.25 ms, 4–70× trên $P_{\max}=-10..-5$ dBm; robust với Rician (K=5 dB: $3.6\times10^{-3}$ vs LoS $1.0\times10^{-3}$, vẫn tốt nhất) | **GO** |

Điểm cần lưu ý khi viết/bảo vệ: (i) so với M-LWDF (bộ lập lịch nhạy đuôi kinh điển) lợi ích của TAS là 1.2–1.8× (đôi khi ngang ở tải rất cao) — đóng góp chính nằm ở kết hợp đặt PA theo tail load + chọn segment/mode theo năng lượng + FBL bundling; (ii) đặt PA nhạy với hình học drop, cần ≥16 drop để so sánh (đã làm); (iii) biến thể tín dụng $Z_k$ và chuẩn hóa PF không cải thiện (đã báo cáo trong bảng độ nhạy).
