# Mô phỏng và Đánh giá Hiệu suất Mạng Edge Computing
---





## Yêu cầu cài đặt

```bash
pip install numpy matplotlib pandas jupyter nbformat python-docx
```

Kiểm tra phiên bản:
```bash
python --version      # cần >= 3.11
python -c "import numpy; print(numpy.__version__)"      # cần >= 1.26
python -c "import matplotlib; print(matplotlib.__version__)"
```

---

## Cách chạy mô phỏng

### 1. Chạy mô phỏng và lưu kết quả ra CSV

```bash
cd simulation
python edge_computing_simulation.py
```

**Kết quả:** In ra bảng số liệu cho 4 kịch bản × 4 thuật toán và lưu vào `results.csv`.

Ý nghĩa các cột trong `results.csv`:

| Cột | Ý nghĩa |
|-----|---------|
| `algorithm` | Tên thuật toán (Round Robin / Random / Least Loaded / Weighted LB) |
| `scenario` | Kịch bản (1–4) |
| `num_users` | Số user (10 / 30 / 60 / 100) |
| `avg_latency_ms` | Độ trễ trung bình (ms) |
| `throughput_mbps` | Thông lượng (Mbps) |
| `avg_cpu_utilization` | Mức dùng CPU trung bình (0.0–1.0) |
| `packet_loss_rate` | Tỷ lệ mất gói (0.0–1.0) |
| `tasks_total` | Tổng số tác vụ phát sinh |
| `tasks_completed` | Số tác vụ xử lý thành công |

> **Lưu ý:** Nếu chạy lại, kết quả có thể khác nhau một chút do seed ngẫu nhiên.  
> File `results.csv` hiện tại là số liệu chính thức dùng trong luận văn — **không cần chạy lại**.

---

### 2. Vẽ lại toàn bộ biểu đồ từ results.csv

```bash
cd simulation
python plot_results.py
```

**Kết quả:** Tạo 6 file PNG trong thư mục `charts/`:
- `latency_line.png` — Đường so sánh độ trễ
- `throughput_line.png` — Đường so sánh thông lượng
- `packet_loss_line.png` — Đường so sánh mất gói
- `cpu_bar.png` — Cột CPU utilization
- `cpu_heatmap.png` — Heatmap CPU
- `radar_comparison.png` — Radar chart so sánh tổng hợp (kịch bản 4)

---

### 3. Chạy Jupyter Notebook (demo tương tác)

```bash
cd simulation
jupyter notebook Edge_Computing_Simulation.ipynb
```

Hoặc mở trực tiếp trong VS Code (cần extension Jupyter).

**Thứ tự chạy:** Nhấn `Kernel → Restart Kernel and Run All Cells` để chạy toàn bộ từ đầu.

**Các cell chính:**

| Cell | Nội dung |
|------|---------|
| 1 | Tiêu đề và mô tả |
| 2 | Import thư viện (NumPy, Pandas, Matplotlib) |
| 3 | Tham số mô phỏng |
| 4 | Định nghĩa class EdgeNode, Task, SimResult |
| 5 | Cấu hình 5 edge node (MIPS, weight) |
| 6 | 4 thuật toán cân bằng tải |
| 7 | Hàm sinh tác vụ và tính latency |
| 8 | Engine mô phỏng chính |
| 9 | Chạy tất cả 16 kịch bản + in kết quả |
| 10 | Vẽ 4 biểu đồ (2×2 grid) |
| 11 | Bảng tóm tắt kịch bản 2 (text) |
| 12 | **Bảng HTML đầy đủ 16 dòng** (có tô màu xanh/đỏ) |
| 13 | **Pivot table** độ trễ và mất gói (heatmap màu) |

---

## Thông số hệ thống mô phỏng

| Tham số | Giá trị |
|---------|---------|
| Thời gian mô phỏng | 1.000 giây |
| Bước thời gian | 1 giây |
| Băng thông | 100 Mbps |
| Trễ lan truyền | 5 ms |
| Dung lượng hàng đợi | 30 tác vụ/node |
| Số edge node | 5 (dị đồng) |
| CPU yêu cầu mỗi task | 100–1.200 MIPS (ngẫu nhiên đều) |
| Kích thước dữ liệu mỗi task | 10–500 KB (ngẫu nhiên đều) |
| Mô hình đến | Poisson với λ = users × 0,5 tasks/s |

**Cấu hình 5 edge node:**

| Node | CPU (MIPS) | Trọng số Weighted LB |
|------|-----------|----------------------|
| 0 | 2.000 | 1,0 |
| 1 | 3.000 | 1,5 |
| 2 | 2.500 | 1,2 |
| 3 | 1.500 | 0,8 |
| 4 | 3.500 | 1,8 |

---

## Kết quả chính (Kịch bản 2 — 30 user, tải trung bình ~78%)

| Thuật toán | Latency (ms) | Throughput (Mbps) | CPU (%) | Loss (%) |
|-----------|-------------|-----------------|---------|---------|
| Round Robin | 2.997 | 28,785 | 79,6 | 4,3 |
| Random | 3.353 | 28,559 | 79,0 | 5,2 |
| **Least Loaded** | **688** | **30,091** | 79,2 | **0,0** |
| Weighted LB | 757 | 30,091 | 78,6 | 0,0 |

**Kết luận ngắn gọn:** Least Loaded giảm độ trễ 4,4 lần và loại bỏ hoàn toàn mất gói so với Round Robin tại mức tải trung bình.

---
