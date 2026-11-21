# Bronze Layer (Raw GIS Data)
## U.S. Drought Monitor (2020 - 2022)

Tầng lưu trữ dữ liệu thô (Raw Ingestion) nguyên bản được thu thập trực tiếp từ cổng GIS chính thức của U.S. Drought Monitor (NDMC / USDA / NOAA / NASA).

---

## 1. Cấu trúc thư mục

```text
bronze/
├── data/
│   ├── shp/                      # 130 thư mục shapefiles hạn hán hàng tuần (M)
│   │   ├── USDM_20200107_M/
│   │   └── ... (đủ 130 tuần đến 28/06/2022)
│   ├── impacts/                  # Shapefiles lớp đối tượng tác động (I)
│   ├── oconus/                   # Shapefiles vùng ngoài lục địa Mỹ (O)
│   └── manifest_download.csv     # Bảng kê trạng thái tải về từ API
├── scripts/
│   ├── crawl_usdm_gis.py         # Crawler tự động đa luồng tải dữ liệu USDM
│   └── inspect_data.py           # Script kiểm tra cấu trúc và metadata shapefiles
└── README.md
```

---

## 2. Đặc tả dữ liệu

- **Định dạng**: ESRI Shapefiles (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`).
- **Hệ quy chiếu (CRS)**: WGS 84 (`EPSG:4326`).
- **Phạm vi thời gian**: 130 tuần liên tục (07/01/2020 – 28/06/2022).
- **Thuộc tính chính**: `DM` (Drought Monitor: `0 = D0`, `1 = D1`, `2 = D2`, `3 = D3`, `4 = D4`).
- **Lưu ý**: Tồn tại 61 hình học tự giao cắt (self-intersection) từ nguồn, sẽ được làm sạch tại Silver Layer.

---

## 3. Cách chạy crawler (khi cần tải bổ sung)

```bash
python bronze/scripts/crawl_usdm_gis.py --start-date 20200107 --end-date 20220628 --workers 8
python bronze/scripts/inspect_data.py
```
