# HƯỚNG DẪN TOÀN DIỆN VỀ DETECT-SECRETS

> **Tài liệu hướng dẫn:** Được tổng hợp và đối chiếu giữa:
> 1. **Mã nguồn mở gốc Yelp `detect-secrets`** (dành cho môi trường phát triển cục bộ và Pre-commit hook).
> 2. **Hiện trạng cấu hình thực tế tại FTECH** (được đối chiếu từ `CI/devsecops-template.yml` và `CI/README.MD`).

---

> [!WARNING]
> ### ⚠️ LƯU Ý PHÂN ĐỊNH GIỮA THƯ VIỆN GỐC (YELP) VÀ IMAGE CI NỘI BỘ (FTECH)
> * **Chương 2, 3, 4, 5 & 7:** Trình bày các câu lệnh CLI, Plugin, Filter và cú pháp Inline Pragma của **thư viện mã nguồn mở Yelp `detect-secrets`**. Phần này cực kỳ hữu ích khi lập trình viên cài đặt trên máy cá nhân (`localhost`), thiết lập Git Pre-commit Hook hoặc xây dựng pipeline độc lập.
> * **Chương 6.1:** Trình bày **cấu hình thực tế 100% đang chạy trên GitLab CI của FTECH** (sử dụng container nội bộ `registry.ftech.ai/public/is-chart/detect-secrets:v2.8` và script `/app/detect-secrets.py`). Do mã nguồn bên trong container image này là nội bộ, việc loại trừ False Positive trên CI của FTECH được xác nhận thực hiện qua 2 biến môi trường `EXCLUDE_SECRETS` và `EXCLUDE_FOLDERS`.

---

## MỤC LỤC

1. [Tổng quan về detect-secrets](#1-tổng-quan-về-detect-secrets)
   - 1.1. detect-secrets là gì?
   - 1.2. Tại sao cần detect-secrets? Khái niệm "Baseline"
   - 1.3. Cơ chế hoạt động cốt lõi
2. [Cài đặt trên máy cá nhân (Local Development)](#2-cài-đặt-trên-máy-cá-nhân-local-development)
   - 2.1. Cài đặt qua pip / brew
   - 2.2. Kiểm tra phiên bản
3. [Bộ 3 Công cụ chính của Yelp CLI](#3-bộ-3-công-cụ-chính-của-yelp-cli)
   - 3.1. `detect-secrets scan` (Quét & Tạo/Cập nhật Baseline)
   - 3.2. `detect-secrets-hook` (Chặn secret trước khi Commit)
   - 3.3. `detect-secrets audit` (Kiểm duyệt & Đánh dấu kết quả)
4. [Hướng dẫn từng bước thiết lập Local & Pre-commit Hook](#4-hướng-dẫn-từng-bước-thiết-lập-local--pre-commit-hook)
   - Bước 1: Quét mã nguồn hiện tại và tạo file `.secrets.baseline`
   - Bước 2: Tích hợp Pre-commit Hook trên máy cá nhân
   - Bước 3: Xử lý khi commit bị chặn do dính Secret
   - Bước 4: Cách loại trừ ngoại lệ nội dòng (Inline Allowlisting trên code)
5. [Cơ chế Phát hiện (Plugins) & Bộ lọc (Filters) của Yelp](#5-cơ-chế-phát-hiện-plugins--bộ-lọc-filters-của-yelp)
   - 5.1. Ba chiến lược phát hiện chính (Regex, Entropy, Keyword)
   - 5.2. Danh sách các Plugins phổ biến
   - 5.3. Bộ lọc loại trừ qua CLI flags (`--exclude-files`, `--exclude-lines`, `--exclude-secrets`)
   - 5.4. Tinh chỉnh ngưỡng Entropy (Base64 / Hex Limits)
6. [Tích hợp detect-secrets trong Hệ thống CI/CD FTECH](#6-tích-hợp-detect-secrets-trong-hệ-thống-cicd-ftech)
   - 6.1. Cấu hình THỰC TẾ tại FTECH (`devsecops-template.yml` & `README.MD`)
   - 6.2. Cơ chế loại trừ False Positive thực tế tại FTECH (`EXCLUDE_SECRETS`, `EXCLUDE_FOLDERS`)
   - 6.3. Ví dụ tham khảo: Tích hợp CLI gốc Yelp vào GitLab CI chung
   - 6.4. Quy trình xử lý chuẩn cho Developer FTECH khi Pipeline CI bị chặn
7. [Bảng tra cứu nhanh lệnh CLI (Cheat Sheet)](#7-bảng-tra-cứu-nhanh-lệnh-cli-cheat-sheet)
8. [Xử lý sự cố thường gặp (Troubleshooting & FAQs)](#8-xử-lý-sự-cố-thường-gặp-troubleshooting--faqs)

---

## 1. TỔNG QUAN VỀ DETECT-SECRETS

### 1.1. detect-secrets là gì?
`detect-secrets` là công cụ chuyên dùng để **tự động quét và phát hiện các thông tin nhạy cảm (secrets)** bị lập trình viên vô tình ghi cứng (hard-code) vào mã nguồn.

Các thông tin nhạy cảm này bao gồm:
* **Mật khẩu (Passwords), Private Keys (SSH, RSA, PGP)**
* **API Keys / Tokens:** AWS Access Key, OpenAI Key, Stripe Token, Slack Token, GitHub/GitLab Token, JWT Token,...
* **Chuỗi ngẫu nhiên có độ hỗn loạn cao (High Entropy Strings):** Các mã hash, chuỗi mã hoá Base64, Hex ngẫu nhiên có nguy cơ là khóa bí mật.

### 1.2. Tại sao cần detect-secrets? Khái niệm "Baseline"
Trong một dự án thực tế quy mô doanh nghiệp:
* Có thể đang tồn tại hàng trăm repository với hàng nghìn dòng code cũ (legacy) đã có sẵn secret giả lập, secret test, hoặc secret cũ chưa kịp dọn dẹp.
* Nếu bật một công cụ quét secret thông thường và chặn toàn bộ, hàng trăm lập trình viên sẽ bị dừng việc (pipeline gãy hàng loạt).

💡 **Giải pháp của `detect-secrets`:** Khái niệm **`.secrets.baseline`** (Điểm chuẩn).
1. Chụp lại toàn bộ các secret hiện có trong codebase vào một file snapshot `.secrets.baseline`.
2. **Chặn tất cả các secret MỚI** phát sinh trong tương lai.
3. Không làm gián đoạn công việc của lập trình viên đối với các dòng code cũ, đồng thời cho phép đội bảo mật lên kế hoạch thu hồi (roll/migrate) các secret cũ dần dần.

```
Mã nguồn hiện tại ──► Quét lần đầu ──► Tạo file .secrets.baseline (Ghi nhận hiện trạng)
                                                 │
Code mới commit / push ──► Đối chiếu baseline ───┤
                                                 ├─► Nếu là secret cũ đã biết ──► CHO QUA
                                                 └─► Nếu là secret MỚI        ──► CHẶN NGAY (BLOCK)
```

---

## 2. CÀI ĐẶT TRÊN MÁY CÁ NHÂN (LOCAL DEVELOPMENT)

### 2.1. Cài đặt qua pip / brew

**Cách 1: Cài qua Python Pip (Khuyên dùng)**
```bash
pip install detect-secrets
```

Nếu muốn cài thêm các tính năng mở rộng (quét từ điển wordlist, nhận diện chuỗi vô nghĩa gibberish):
```bash
pip install "detect-secrets[word_list]"
pip install "detect-secrets[gibberish]"
```

**Cách 2: Cài qua Homebrew (Dành cho macOS / Linux)**
```bash
brew install detect-secrets
```

### 2.2. Kiểm tra phiên bản
```bash
detect-secrets --version
```

---

## 3. BỘ 3 CÔNG CỤ CHÍNH CỦA YELP CLI

> [!NOTE]
> Các lệnh bên dưới là các công cụ dòng lệnh (CLI) chính thức của Yelp `detect-secrets`, sử dụng khi chạy trên terminal máy cá nhân hoặc trong container tùy biến.

| Lệnh | Mục đích | Khi nào dùng? |
| :--- | :--- | :--- |
| **`detect-secrets scan`** | Quét mã nguồn và xuất ra file JSON baseline | Khi khởi tạo dự án hoặc cập nhật lại baseline |
| **`detect-secrets-hook`** | Kiểm tra danh sách file và báo lỗi nếu có secret mới | Chạy trong Git Pre-commit hook trước khi commit |
| **`detect-secrets audit`** | Giao diện tương tác để phân loại Secret thật (True Positive) hay Giả (False Positive) | Dành cho Security / DevLead review lại các secret tìm thấy |

---

## 4. HƯỚNG DẪN TỪNG BƯỚC THIẾT LẬP LOCAL & PRE-COMMIT HOOK

### Bước 1: Quét mã nguồn hiện tại và tạo file baseline

Di chuyển vào thư mục gốc của repository và chạy lệnh:

```bash
detect-secrets scan > .secrets.baseline
```

*File `.secrets.baseline` là file JSON chứa danh sách các hash của secret đã tìm thấy, vị trí dòng, loại plugin nhận diện.*

> **Mẹo:** Nếu bạn muốn quét cả những file chưa được `git add`, thêm cờ `--all-files`:
> ```bash
> detect-secrets scan --all-files > .secrets.baseline
> ```

---

### Bước 2: Tích hợp Pre-commit Hook trên máy cá nhân

Để ngăn chặn secret ngay từ máy lập trình viên trước khi đẩy lên GitLab:

1. Cài đặt thư viện `pre-commit`:
   ```bash
   pip install pre-commit
   ```

2. Tạo file `.pre-commit-config.yaml` tại thư mục gốc dự án:
   ```yaml
   repos:
   - repo: https://github.com/Yelp/detect-secrets
     rev: v1.5.0
     hooks:
     - id: detect-secrets
       args: ['--baseline', '.secrets.baseline']
       exclude: package-lock.json|yarn.lock|pnpm-lock.yaml
   ```

3. Kích hoạt hook:
   ```bash
   pre-commit install
   ```

Từ nay, mỗi khi gõ `git commit`, `detect-secrets` sẽ tự động kiểm tra các file trong vùng staging.

---

### Bước 3: Xử lý khi commit bị chặn do dính Secret

Khi bạn commit một đoạn code chứa secret, hệ thống sẽ báo lỗi:

```text
ERROR: Potential secrets about to be committed to git repo!

Secret Type: AWSKeyDetector
Location:    src/config.py:14

Please mitigate this before committing, or update your baseline.
```

**Cách khắc phục:**
1. **Nếu là Secret thật:** Xóa secret ra khỏi code ngay lập tức, chuyển sang đọc từ biến môi trường (Environment Variable) hoặc Secret Manager.
2. **Nếu là Secret giả (False Positive - token test, mock data):** Sử dụng **Inline Allowlisting** (xem Bước 4).
3. **Nếu muốn đưa secret này vào baseline chấp nhận trước:** Cập nhật lại baseline:
   ```bash
   detect-secrets scan --baseline .secrets.baseline
   git add .secrets.baseline
   ```

---

### Bước 4: Cách loại trừ ngoại lệ nội dòng (Inline Allowlisting)

> [!NOTE]
> Cú pháp `# pragma: allowlist secret` được hỗ trợ bởi engine Yelp `detect-secrets` khi quét trên file nguồn.

#### Dạng 1: Bỏ qua ngay trên cùng một dòng (`pragma: allowlist secret`)

* **Python:**
  ```python
  API_KEY_TEST = "AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret
  ```

* **JavaScript / TypeScript / Java / C# / Golang:**
  ```javascript
  const fakeSecret = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."; // pragma: allowlist secret
  ```

* **YAML / Shell Script:**
  ```yaml
  mock_token: "dGhpcyBpcyBhIG1vY2sgdG9rZW4=" # pragma: allowlist secret
  ```

#### Dạng 2: Bỏ qua cho dòng kế tiếp (`pragma: allowlist nextline secret`)

* **Python:**
  ```python
  # pragma: allowlist nextline secret
  JWT_SECRET_SAMPLE = "c29tZXJhbmRvbWhleHN0cmluZzEyMzQ1Njc4OQ=="
  ```

---

## 5. CƠ CHẾ PHÁT HIỆN (PLUGINS) & BỘ LỌC (FILTERS) CỦA YELP

### 5.1. Ba chiến lược phát hiện chính

```
                       ┌────────────────────────────────────────────────────────┐
                       │             CHIẾN LƯỢC PHÁT HIỆN SECRET                │
                       └──────────────────────────┬─────────────────────────────┘
                                                  │
         ┌────────────────────────────────────────┼────────────────────────────────────────┐
         │                                        │                                        │
         ▼                                        ▼                                        ▼
┌──────────────────┐                     ┌──────────────────┐                     ┌──────────────────┐
│   1. REGEX RULES │                     │2. SHANNON ENTROPY│                     │3. KEYWORD DETECT │
├──────────────────┤                     ├──────────────────┤                     ├──────────────────┤
│ Nhận diện theo   │                     │ Đo độ ngẫu nhiên │                     │ Tìm theo tên     │
│ cú pháp đặc thù: │                     │ /hỗn loạn chuỗi: │                     │ biến nhạy cảm:   │
│ AWS Key, JWT,    │                     │ Base64, Hex      │                     │ password=...,    │
│ OpenAI, Private  │                     │ ngẫu nhiên dài.  │                     │ api_key=...      │
│ Key,...          │                     │                  │                     │                  │
└──────────────────┘                     └──────────────────┘                     └──────────────────┘
```

### 5.2. Danh sách các Plugins phổ biến

Để xem toàn bộ plugin đang hỗ trợ trong CLI:
```bash
detect-secrets scan --list-all-plugins
```

Các plugin tiêu biểu:
* `AWSKeyDetector`: Phát hiện AWS Access Key (`AKIA...`)
* `OpenAIDetector`: Phát hiện OpenAI API Key (`sk-...`)
* `GitHubTokenDetector` / `GitLabTokenDetector`: Phát hiện Personal Access Token
* `JwtTokenDetector`: Phát hiện JSON Web Token
* `PrivateKeyDetector`: Phát hiện khối mã `-----BEGIN RSA PRIVATE KEY-----`
* `Base64HighEntropyString`: Phát hiện chuỗi Base64 ngẫu nhiên có độ dài bất thường
* `HexHighEntropyString`: Phát hiện chuỗi Hex ngẫu nhiên
* `KeywordDetector`: Phát hiện phép gán biến chứa từ khóa `password`, `secret`, `api_key`, `token`,...

### 5.3. Bộ lọc loại trừ qua CLI flags

Khi chạy `detect-secrets scan` độc lập:
* **Loại trừ file:** `--exclude-files '.*\.lock$' --exclude-files 'docs/.*'`
* **Loại trừ dòng:** `--exclude-lines 'password = fake'`
* **Loại trừ giá trị secret:** `--exclude-secrets '\${.*}'`

### 5.4. Tinh chỉnh ngưỡng Entropy

Độ hỗn loạn chuỗi (Entropy) mặc định:
* **Base64:** `4.5` (Thang đo `0.0` - `8.0`)
* **Hex:** `3.0` (Thang đo `0.0` - `8.0`)

Nâng ngưỡng để giảm cảnh báo giả:
```bash
detect-secrets scan --base64-limit 5.0 --hex-limit 3.5 > .secrets.baseline
```

---

## 6. TÍCH HỢP DETECT-SECRETS TRONG HỆ THỐNG CI/CD FTECH

### 6.1. Cấu hình THỰC TẾ tại FTECH (`devsecops-template.yml` & `README.MD`)

Trong repository CI tập trung của FTECH, job `detect-secrets` được khai báo chính xác như sau trong [devsecops-template.yml](file:///d:/FTECH/CI-CD/CI/devsecops-template.yml):

```yaml
detect-secrets:
  stage: detect-secrets
  image:
    name: registry.ftech.ai/public/is-chart/detect-secrets:v2.8
  script:
    - rm -rf .git/
    - python /app/detect-secrets.py
  tags: [devsecops]
  allow_failure: false
```

#### Phân tích hiện trạng thực tế FTECH:
1. **Container Image nội bộ:** Sử dụng `registry.ftech.ai/public/is-chart/detect-secrets:v2.8` do đội ngũ kỹ thuật FTECH đóng gói sẵn.
2. **Script thực thi nội bộ:** Chạy `python /app/detect-secrets.py`.
3. **Thao tác `rm -rf .git/`:** Trước khi chạy script, pipeline xóa thư mục `.git/`. Điều này cho thấy script nội bộ hoạt động bằng cách **quét trực tiếp trên toàn bộ cây thư mục (filesystem)** mà không phụ thuộc vào lịch sử git commit hay `git diff`.
4. **Chính sách chặn gắt gao (`allow_failure: false`):** Bắt buộc phải vượt qua bước này, nếu phát hiện secret thì pipeline sẽ dừng ngay lập tức và báo đỏ (Fail).

---

### 6.2. Cơ chế loại trừ False Positive THỰC TẾ tại FTECH

Theo hướng dẫn chính thức trong [README.MD](file:///d:/FTECH/CI-CD/CI/README.MD) của FTECH, cách cấu hình loại trừ (False Positive Exclusion) cho stage `detect-secrets` là **khai báo qua biến môi trường CI/CD (CI Variables)**:

```yaml
# Khai báo trong .gitlab-ci.yml của dự án hoặc trên GitLab UI:
variables:
  # Loại trừ các chuỗi secret giả, ngăn cách nhau bởi dấu gạch đứng |
  EXCLUDE_SECRETS: "bckjxzbkjcq8228rja0czxi13h23roihsaoasjk|12345678Aa"

  # Loại trừ các thư mục không cần quét, ngăn cách nhau bởi dấu chấm phẩy ;
  EXCLUDE_FOLDERS: "static;store/static;abcd"
```

#### Cách cấu hình trên GitLab UI:
1. Vào dự án trên GitLab: **Settings** > **CI/CD** > **Variables**.
2. Thêm key `EXCLUDE_SECRETS` hoặc `EXCLUDE_FOLDERS` với giá trị tương ứng.
3. Chạy lại Pipeline (Retry).

---

### 6.3. Ví dụ tham khảo: Tích hợp CLI gốc Yelp vào GitLab CI chung

> [!NOTE]
> Đây là cấu hình mẫu generic dành cho các dự án muốn chạy trực tiếp thư viện Yelp chuẩn với file `.secrets.baseline` (không dùng image nội bộ FTECH):

```yaml
detect-secrets-generic-job:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install detect-secrets
  script:
    - |
      if [ -f ".secrets.baseline" ]; then
        echo "Kiểm tra với baseline..."
        git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline
      else
        echo "Quét toàn bộ repo..."
        detect-secrets scan --all-files > temp_baseline.json
        COUNT=$(python -c "import json; data=json.load(open('temp_baseline.json')); print(sum(len(v) for v in data.get('results', {}).values()))")
        if [ "$COUNT" -gt "0" ]; then
          echo "PHÁT HIỆN $COUNT SECRET TRONG CODE!"
          exit 1
        fi
      fi
  allow_failure: false
```

---

### 6.4. Quy trình xử lý chuẩn cho Developer FTECH khi Pipeline CI bị chặn

Khi một Pipeline CI tại FTECH bị Fail ở stage `detect-secrets`:

```
                    ┌──────────────────────────────────────────────┐
                    │       JOB DETECT-SECRETS BỊ THẤT BẠI         │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                     Mở Job Log trên GitLab xem chi tiết file & dòng vi phạm
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         │                                                                   │
         ▼                                                                   ▼
[Trường hợp A: Secret THẬT]                                       [Trường hợp B: Secret GIẢ / Thư mục Test]
1. Xóa ngay secret khỏi mã nguồn.                                 1. Cấu hình biến môi trường CI:
2. Chuyển sang dùng biến GitLab CI Variables:                        - `EXCLUDE_SECRETS`: "chuoi_secret_gia"
   (Settings > CI/CD > Variables).                                   - `EXCLUDE_FOLDERS`: "thu_muc_test"
3. Thu hồi (Revoke/Rotate) secret bị lộ ngay lập tức.             2. Hoặc thêm inline pragma nếu code hỗ trợ:
4. Commit và Push lại mã nguồn sạch.                                 `# pragma: allowlist secret`
                                                                  3. Re-run lại Pipeline trên GitLab.
```

---

## 7. BẢNG TRA CỨU NHANH LỆNH CLI (CHEAT SHEET)

| Thao tác (Môi trường Local / Yelp CLI) | Câu lệnh Terminal |
| :--- | :--- |
| **Quét và tạo file baseline mới** | `detect-secrets scan > .secrets.baseline` |
| **Quét toàn bộ file (kể cả file chưa commit)** | `detect-secrets scan --all-files > .secrets.baseline` |
| **Cập nhật lại file baseline hiện có** | `detect-secrets scan --baseline .secrets.baseline` |
| **Kiểm tra các file trong Git Staging** | `git diff --staged --name-only -z \| xargs -0 detect-secrets-hook --baseline .secrets.baseline` |
| **Kiểm tra tất cả các file đã track trong Git** | `git ls-files -z \| xargs -0 detect-secrets-hook --baseline .secrets.baseline` |
| **Xem danh sách tất cả các plugin** | `detect-secrets scan --list-all-plugins` |
| **Tắt một plugin cụ thể (VD: KeywordDetector)** | `detect-secrets scan --disable-plugin KeywordDetector` |
| **Loại trừ một thư mục hoặc đuôi file** | `detect-secrets scan --exclude-files 'tests/.*' --exclude-files '.*\.json$'` |
| **Chế độ kiểm duyệt tương tác (Interactive Audit)** | `detect-secrets audit .secrets.baseline` |
| **Xem báo cáo thống kê các secret trong baseline** | `detect-secrets audit --report --stats .secrets.baseline` |

---

## 8. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING & FAQS)

### Q1: Cấu hình loại trừ trên CI FTECH bằng cách nào nhanh nhất?
* **Trả lời:** Vào GitLab repository của dự án > **Settings** > **CI/CD** > **Variables**, khai báo biến `EXCLUDE_SECRETS` (ví dụ: `secret1|secret2`) hoặc `EXCLUDE_FOLDERS` (ví dụ: `static;tests;docs`).

### Q2: Tại sao `detect-secrets audit` báo lỗi "Not a valid baseline file!" trên Windows?
* **Nguyên nhân:** File `.secrets.baseline` được lưu với encoding UTF-16 (mặc định của toán tử `>` trên PowerShell cũ).
* **Khắc phục:** Sử dụng Git Bash hoặc chỉ định UTF-8 trong PowerShell:
  ```powershell
  detect-secrets scan | Out-File -Encoding utf8 .secrets.baseline
  ```

### Q3: Tôi đã chuyển secret sang biến môi trường, tại sao lệnh scan vẫn báo lỗi?
* **Nguyên nhân:** Tên biến chứa từ khóa nhạy cảm (như `password = ""`) kích hoạt `KeywordDetector`.
* **Khắc phục:** Thêm `# pragma: allowlist secret` vào cuối dòng hoặc đưa chuỗi vào biến `EXCLUDE_SECRETS`.
