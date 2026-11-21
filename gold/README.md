# Gold Layer (Curated / ML-Ready Gridded Mart)
## U.S. Drought Monitor (2020 - 2022)

Tầng dữ liệu tinh luyện (Curated Mart) phục vụ trực tiếp cho huấn luyện mô hình học máy không gian - thời gian (Spatio-Temporal Graph Neural Networks, LSTM, v.v.) dự báo hạn hán.

---

## 1. Cấu trúc thư mục

```text
gold/
├── data/
│   ├── usdmfinal.csv             # Bảng phẳng chuỗi thời gian lưới 0.5° (423.670 dòng)
│   ├── A.csv                     # Ma trận kề láng giềng giữa 3.259 ô hợp lệ
│   ├── USDMRasterized.rda        # File R data lưu trữ đối tượng raster trung gian
│   ├── validation.txt            # Thống kê phân bố nhãn hạn hán
│   └── comparison_reports/       # Các file đối sánh với benchmark dataset cũ
│       ├── comparison_by_week.csv
│       ├── comparison_differences.csv
│       ├── comparison_drought_matrix.csv
│       └── comparison_summary.json
├── scripts/
│   ├── RasterizeUSDM_2020_2022.R # Script R rasterize đa giác lên lưới không gian
│   ├── input_manifest.csv        # Danh sách 130 tuần dữ liệu đầu vào
│   └── sessionInfo.txt           # Nhật ký phiên bản thư viện R
└── README.md
```

---

## 2. Đặc tả dữ liệu

- **Khung lưới không gian**: 120 cột × 50 hàng = 6.000 ô (độ phân giải 0.5° × 0.5° trên bounding box `[-125, -65, 25, 50]`).
- **Mặt nạ lục địa Mỹ**: Mask các bang CONUS và loại trừ 5 ô biển (`S2, S105, EE97, KK88, RR85`), giữ lại đúng **3.259 ô đất liền hợp lệ**.
- **Kích thước file `usdmfinal.csv`**: $130 \text{ tuần} \times 3.259 \text{ ô} = \mathbf{423.670 \text{ dòng}}$.
- **Các cột**:
  - `time`: Ngày công bố (YYYYMMDD).
  - `grid`: Mã định danh ô lưới (ví dụ: `C6`, `D10`).
  - `lon`: Kinh độ tâm ô.
  - `lat`: Vĩ độ tâm ô.
  - `drought`: Nhãn hạn hán (`0` = Không hạn, `D0` đến `D4`).
- **Ma trận kề `A.csv`**: Ma trận kề không gian $3.259 \times 3.259$, ô láng giềng cạnh hoặc chéo nhận giá trị `1`.

---

## 3. Cách chạy tái tạo Gold Layer (bằng R)

```powershell
$env:LC_ALL = 'English_United States.utf8'
& '..\.r_runtime\R\bin\Rscript.exe' --vanilla 'gold\scripts\RasterizeUSDM_2020_2022.R'
```
