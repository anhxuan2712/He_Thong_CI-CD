# HƯỚNG DẪN TOÀN DIỆN VỀ TRIVY CHO NGƯỜI MỚI BẮT ĐẦU

> **Tài liệu hướng dẫn thực hành DevSecOps:** Được tổng hợp và đối chiếu từ:
> 1. **Tài liệu mã nguồn mở chính thức của Aqua Security Trivy** (quét lỗ hổng, SBOM, cấu hình sai, secret).
> 2. **Hiện trạng cấu hình thực tế tại FTECH** (được đối chiếu từ job `dependency-check` và `upload-bom` trong `CI/devsecops-template.yml`).

---

## MỤC LỤC

1. [Tổng quan về Trivy](#1-tổng-quan-về-trivy)
   - 1.1. Trivy là gì?
   - 1.2. Tại sao Trivy trở thành tiêu chuẩn vàng trong DevSecOps?
   - 1.3. Mô hình Target vs Scanner
   - 1.4. Khái niệm CVE, Severity và SBOM
2. [Cài đặt & Chuẩn bị môi trường](#2-cài-đặt--chuẩn-bị-môi-trường)
   - 2.1. Cài đặt trên máy cá nhân (Windows / macOS / Linux)
   - 2.2. Chạy nhanh qua Docker Container
   - 2.3. Cơ chế tải và cập nhật Vulnerability Database (DB)
3. [Hướng dẫn sử dụng các lệnh cốt lõi (Core Commands)](#3-hướng-dẫn-sử-dụng-các-lệnh-cốt-lõi-core-commands)
   - 3.1. Quét mã nguồn & thư viện phụ thuộc (`trivy fs` / `trivy filesystem`)
   - 3.2. Quét Container Image (`trivy image`)
   - 3.3. Quét Git Repository từ xa (`trivy repo`)
   - 3.4. Xuất file báo cáo SBOM chuẩn quốc tế (`CycloneDX`, `SPDX`)
4. [Các tham số dòng lệnh quan trọng (Essential Flags)](#4-các-tham-số-dòng-lệnh-quan-trọng-essential-flags)
   - 4.1. Lọc theo mức độ nghiêm trọng (`--severity` / `-s`)
   - 4.2. Bỏ qua lỗ hổng chưa có bản vá (`--ignore-unfixed`)
   - 4.3. Điều khiển mã thoát trong CI/CD (`--exit-code`)
   - 4.4. Định dạng đầu ra (`--format` & `--output`)
   - 4.5. Cơ chế bỏ qua lỗ hổng qua file `.trivyignore`
5. [Phân tích Cấu hình THỰC TẾ tại FTECH (`devsecops-template.yml`)](#5-phân-tích-cấu-hình-thực-tế-tại-ftech-devsecops-templateyml)
   - 5.1. Job `dependency-check` (Stage quét lỗ hổng & sinh SBOM)
   - 5.2. Job `upload-bom` (Stage đẩy SBOM lên OWASP Dependency-Track)
   - 5.3. Phân tích chi tiết từng cờ lệnh trong cấu hình FTECH
   - 5.4. Đánh giá chính sách bảo mật (`allow_failure: true` vs `allow_failure: false`)
6. [Quy trình xử lý lỗ hổng (Vulnerability Remediation Guide)](#6-quy-trình-xử-lý-lỗ-hổng-vulnerability-remediation-guide)
   - 6.1. Cách đọc bảng kết quả quét của Trivy
   - 6.2. 3 Bước xử lý triệt để lỗ hổng cho Developer
   - 6.3. Cách tạo file `.trivyignore` để xử lý False Positive / Accepted Risk
7. [Bảng tra cứu nhanh lệnh (Cheat Sheet)](#7-bảng-tra-cứu-nhanh-lệnh-cheat-sheet)
8. [Xử lý sự cố thường gặp (Troubleshooting & FAQs)](#8-xử-lý-sự-cố-thường-gặp-troubleshooting--faqs)

---

## 1. TỔNG QUAN VỀ TRIVY

### 1.1. Trivy là gì?
**Trivy** (phát âm: *tri-vee*, do Aqua Security phát triển) là công cụ quét bảo mật **All-in-One (Tất cả trong một)** hàng đầu thế giới hiện nay. Trivy giúp phát hiện các lỗ hổng bảo mật đã biết (CVE), cấu hình sai (misconfigurations), lộ secret và phân tích bản kê khai phần mềm (SBOM).

### 1.2. Tại sao Trivy trở thành tiêu chuẩn vàng trong DevSecOps?
* **Tốc độ cực nhanh & Tiêu tốn ít tài nguyên:** Được viết bằng Go, khởi động chỉ trong vài giây.
* **Độ chính xác cao:** Nguồn dữ liệu lỗ hổng liên tục cập nhật từ NVD, Red Hat, Debian, Ubuntu, Alpine, GitHub Advisory Database,...
* **Hỗ trợ đa nền tảng & ngôn ngữ:** Quét mọi package manager (npm/yarn/pnpm, pip/poetry, maven/gradle, gomod, composer, nuget, rubygems, cargo,...).
* **Tích hợp sẵn SBOM:** Xuất chuẩn **CycloneDX** và **SPDX** để tích hợp trực tiếp vào các hệ thống quản lý rủi ro chuỗi cung ứng phần mềm như **OWASP Dependency-Track**.

---

### 1.3. Mô hình Target vs Scanner

Trivy được thiết kế theo cấu trúc module tách bạch giữa **5 Đối tượng quét (Targets)** và **4 Loại hình quét (Scanners)**:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       ĐỐI TƯỢNG QUÉT (5 TARGETS)                                       │
├───────────────────┬───────────────────┬───────────────────┬───────────────────┬────────────────────────┤
│  Filesystem (fs)  │  Container Image  │  Git Repo (repo)  │  VM Image (vm)    │ Kubernetes (k8s)       │
│  (Thư mục mã nguồn│  (Docker Image    │  (Quét từ xa qua  │  (Ảnh đĩa máy ảo  │ (Tài nguyên cụm k8s    │
│   & file lock)    │   local/registry) │   URL Git)        │   AWS AMI, VMDK)  │  đang hoạt động)       │
└─────────┬─────────┴─────────┬─────────┴─────────┬─────────┴─────────┬─────────┴───────────┬────────────┘
          │                   │                   │                   │                     │
          └───────────────────┴───────────────────┼───────────────────┴─────────────────────┘
                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       LOẠI HÌNH QUÉT (4 SCANNERS)                                      │
├───────────────────┬───────────────────┬───────────────────┬────────────────────────────────────────────┤
│    vuln (CVEs)    │ misconfig (IaC)   │   secret (Rò rỉ)  │   license (Giấy phép)                      │
│  Lỗ hổng thư viện │ Sai cấu hình K8s, │ Mật khẩu, API Key,│ Kiểm tra vi phạm bản quyền                 │
│  & OS packages    │ Dockerfile, Tform │ Private Tokens    │ phần mềm (GPL, MIT, Apache,...)            │
└───────────────────┴───────────────────┴───────────────────┴────────────────────────────────────────────┘
```

---

### 1.4. Khái niệm CVE, Severity và SBOM

#### 1. CVE (Common Vulnerabilities and Exposures)
Là mã định danh duy nhất toàn cầu cho một lỗ hổng bảo mật đã được công bố công khai (ví dụ: `CVE-2021-44228` - lỗ hổng Log4j khét tiếng).

#### 2. Thang đo mức độ nghiêm trọng (Severity Levels)
Trivy phân loại mức độ rủi ro thành **5 mức riêng biệt** theo chuẩn CVSS (có thể lọc độc lập qua cờ `--severity`):
* ⚪ **UNKNOWN:** Lỗ hổng chưa được đánh giá chính thức hoặc chưa có chỉ số CVSS cụ thể.
* 🔵 **LOW:** Rủi ro rất thấp, khó khai thác hoặc chỉ gây ảnh hưởng nhỏ, không tác động trực tiếp đến dữ liệu.
* 🟡 **MEDIUM:** Lỗ hổng mức trung bình, thường đòi hỏi điều kiện môi trường hoặc tương tác người dùng nhất định để khai thác.
* 🟠 **HIGH:** Lỗ hổng nguy hiểm, có thể dẫn đến rò rỉ dữ liệu quan trọng hoặc gây từ chối dịch vụ (DoS).
* 🔴 **CRITICAL:** CỰC KỲ NGUY HIỂM! Cho phép kẻ tấn công thực thi mã từ xa (RCE) hoặc chiếm toàn quyền điều khiển hệ thống mà không cần xác thực.

#### 3. SBOM (Software Bill of Materials)
SBOM được ví như **"bảng thành phần dinh dưỡng trên bao bì thực phẩm"** của phần mềm. Nó liệt kê toàn bộ danh sách các thư viện, phiên bản, tác giả và mối liên hệ phụ thuộc trong dự án. Hai định dạng SBOM chuẩn quốc tế phổ biến nhất là **CycloneDX** và **SPDX**.

---

## 2. CÀI ĐẶT & CHUẨN BỊ MÔI TRƯỜNG

### 2.1. Cài đặt trên máy cá nhân

#### Trên macOS (Homebrew):
```bash
brew install trivy
```

#### Trên Linux (Ubuntu/Debian):
```bash
sudo apt-get install wget apt-transport-https gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

#### Trên Windows (Winget hoặc Chocolatey):
```powershell
winget install AquaSecurity.Trivy
# Hoặc:
choco install trivy
```

### 2.2. Chạy nhanh qua Docker Container (Không cần cài đặt CLI)
```bash
# Quét thư mục hiện tại:
docker run --rm -v $(pwd):/workspace -w /workspace aquasec/trivy:latest fs .

# Quét một Docker Image:
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image nginx:latest
```

### 2.3. Cơ chế tải và cập nhật Vulnerability Database (DB)
Lần đầu tiên chạy, Trivy sẽ tự động tải cơ sở dữ liệu lỗ hổng về máy. Nếu muốn chủ động tải trước DB mà không quét:
```bash
trivy image --download-db-only
```

---

## 3. HƯỚNG DẪN SỬ DỤNG CÁC LỆNH CỐT LÕI (CORE COMMANDS)

### 3.1. Quét mã nguồn & Thư viện phụ thuộc (`trivy fs`)
Đây là lệnh quét thư mục dự án trên ổ cứng (dựa vào `package-lock.json`, `pom.xml`, `requirements.txt`, `go.sum`,...):

```bash
# Quét toàn bộ thư mục hiện tại
trivy fs .

# Chỉ quét lỗ hổng thư viện (bỏ qua quét secret/misconfig)
trivy fs --scanners vuln .
```

### 3.2. Quét Container Image (`trivy image`)
Quét cả hệ điều hành bên trong image (OS packages như alpine, debian) lẫn thư viện ứng dụng:

```bash
# Quét image trên máy hoặc trên Docker Hub
trivy image python:3.11-alpine

# Quét image từ Private Harbor Registry (yêu cầu docker login trước)
# Sử dụng đúng cấu trúc namespace /public/ chuẩn FTECH:
trivy image registry.ftech.ai/public/is-chart/api-service:v1.0.0
```

### 3.3. Quét Git Repository từ xa (`trivy repo`)
Quét trực tiếp một repository từ xa mà không cần clone về máy:
```bash
trivy repo https://github.com/gin-gonic/gin
```

### 3.4. Xuất file báo cáo SBOM chuẩn quốc tế
Trivy có khả năng đọc toàn bộ dependency và xuất ra file SBOM chuẩn **CycloneDX JSON** (được FTECH sử dụng):

```bash
trivy fs --format cyclonedx --output sbom-result.json .
```

---

## 4. CÁC THAM SỐ DÒNG LỆNH QUAN TRỌNG (ESSENTIAL FLAGS)

| Cờ lệnh (Flag) | Ý nghĩa | Ví dụ thực tế |
| :--- | :--- | :--- |
| **`-s` / `--severity`** | Chỉ lọc kết quả theo mức độ rủi ro mong muốn | `-s HIGH,CRITICAL` |
| **`--ignore-unfixed`** | Bỏ qua các lỗ hổng chưa có bản vá từ nhà sản xuất (giúp giảm nhiễu) | `--ignore-unfixed` |
| **`--exit-code`** | Mã thoát trả về khi phát hiện lỗi (`0`: thành công, `1`: báo lỗi chặn pipeline) | `--exit-code 1` |
| **`--scanners`** | Chọn loại máy quét (`vuln`, `misconfig`, `secret`, `license`) | `--scanners vuln` |
| **`--format`** | Định dạng hiển thị (`table`, `json`, `cyclonedx`, `spdx`, `sarif`) | `--format cyclonedx` |
| **`-o` / `--output`** | Đường dẫn file lưu kết quả | `--output result.json` |
| **`--quiet`** | Tắt các thông báo tiến trình / log thừa | `--quiet` |
| **`--cache-dir`** | Chỉ định thư mục lưu cache của cơ sở dữ liệu | `--cache-dir /root/.cache/trivy` |

---

## 5. PHÂN TÍCH CẤU HÌNH THỰC TẾ TẠI FTECH (`devsecops-template.yml`)

Trong hệ thống CI/CD FTECH ([devsecops-template.yml](file:///d:/FTECH/CI-CD/CI/devsecops-template.yml)), quy trình quét lỗ hổng phụ thuộc và đẩy báo cáo được thực hiện qua **2 Stages liên hoàn**:

```
[Mã nguồn ứng dụng] ──► [Job 1: dependency-check] ──► Xuất file SBOM (result1.json)
                                                              │
                                                              ▼
                        [Job 2: upload-bom]        ◄──────────┘
                        Đẩy SBOM lên Server
                        OWASP Dependency-Track
```

---

### 5.1. Job `dependency-check` (Quét & Xuất SBOM)

```yaml
variables:
  RESULT: "./result1.json"

dependency-check:
  stage: dependency-check
  image:
    name: aquasec/trivy:0.56.1
    entrypoint: [""]
  before_script:
    - trivy image --quiet --download-db-only --debug
  script:
    - trivy filesystem --format cyclonedx --output ./result.json --quiet --exit-code 0 --no-progress --cache-dir /root/.cache/trivy --scanners vuln --ignore-unfixed -s HIGH,CRITICAL .
    - cat ./result.json > $RESULT
  artifacts:
    paths:
      - $RESULT
  tags: [devsecops]
  allow_failure: true
```

#### Phân tích chi tiết từng bước thực thi:
1. **`image: aquasec/trivy:0.56.1`:** Sử dụng image chính thức từ Aqua Security bản `v0.56.1` với `entrypoint: [""]` để Runner có thể chạy lệnh tùy biến.
2. **`before_script: trivy image --quiet --download-db-only --debug`:** Tải sẵn DB lỗ hổng về trước trong chế độ im lặng.
3. **`trivy filesystem ...`:** 
   - `--format cyclonedx --output ./result.json`: Xuất danh mục phần mềm và lỗ hổng theo chuẩn quốc tế CycloneDX.
   - `--scanners vuln`: Chỉ tập trung dò quét lỗ hổng bảo mật thư viện (bỏ qua misconfig/secret vì secret đã có job `detect-secrets` đảm nhiệm).
   - `--ignore-unfixed`: Bỏ qua các CVE chưa có cách sửa để không làm phiền lập trình viên.
   - `-s HIGH,CRITICAL`: Chỉ lọc các lỗ hổng ở mức độ **Nặng (HIGH)** và **Cực kỳ nghiêm trọng (CRITICAL)**.
   - `--exit-code 0`: Luôn trả về 0 để job không bị đỏ ngay tại đây.
4. **`artifacts:`:** Lưu file `result1.json` lại để truyền sang job tiếp theo.

---

### 5.2. Job `upload-bom` (Đẩy lên Dependency-Track)

```yaml
upload-bom:
  stage: upload-bom
  image:
    name: curlimages/curl
    entrypoint: [""]
  script:
    - cat result1.json
    - curl -X "POST" "https://dependency-track.dev.ftech.ai/api/v1/bom" \
        -H "Content-Type:multipart/form-data" \
        -H "X-Api-Key:$DEPENDENCY_TRACK_KEY" \
        -F "autoCreate=true" \
        -F "projectName=$CI_PROJECT_NAME" \
        -F "description=abcd" \
        -F "bom=@result1.json"
  tags: [devsecops]
  allow_failure: true
```

* **Mục đích:** Gửi file BOM `result1.json` vừa tạo qua REST API lên hệ thống **OWASP Dependency-Track** nội bộ (`https://dependency-track.dev.ftech.ai`).
* **Ý nghĩa:** Giúp đội ngũ Security và TechLead có bảng điều khiển (Dashboard) tập trung theo dõi tình trạng lỗ hổng của tất cả các microservices trong công ty theo thời gian thực.

---

### 5.3. Đánh giá chính sách bảo mật (`allow_failure: true` vs `false`)

> [!NOTE]
> * Trong cấu hình hiện tại của FTECH, cả hai job `dependency-check` và `upload-bom` đều được gán cờ **`allow_failure: true`** (Soft Gate).
> * **Ưu điểm:** Không làm gián đoạn tiến độ release sản phẩm khi các thư viện bên thứ 3 phát sinh lỗ hổng mới.
> * **Khuyến nghị tương lai (Hard Gate):** Đối với nhánh `main/prod`, nên cân nhắc đổi thành `allow_failure: false` kết hợp kiểm duyệt để đảm bảo tuyệt đối không có lỗ hổng CRITICAL nào lọt vào môi trường Production.

---

## 6. QUY TRÌNH XỬ LÝ LỖ HỔNG (VULNERABILITY REMEDIATION GUIDE)

### 6.1. Cách đọc bảng kết quả quét của Trivy

Khi chạy Trivy trên máy hoặc xem log, bảng kết quả sẽ có cấu trúc như sau:

```text
Target: package-lock.json
┌────────────────┬────────────────┬──────────┬───────────────────┬───────────────┬────────────────────────────────────────────────────────┐
│    Library     │ Vulnerability  │ Severity │ Installed Version │ Fixed Version │                         Title                          │
├────────────────┼────────────────┼──────────┼───────────────────┼───────────────┼────────────────────────────────────────────────────────┤
│ axios          │ CVE-2023-45857 │ CRITICAL │ 0.21.1            │ 1.6.0         │ Axios Cross-Site Request Forgery Vulnerability         │
│ express        │ CVE-2022-24999 │ HIGH     │ 4.17.1            │ 4.18.2        │ qs vulnerable to Prototype Pollution                   │
└────────────────┴────────────────┴──────────┴───────────────────┴───────────────┴────────────────────────────────────────────────────────┘
```

* **Library:** Thư viện bị dính lỗi.
* **Vulnerability:** Mã CVE định danh lỗ hổng.
* **Severity:** Mức độ nguy hiểm (`CRITICAL` hoặc `HIGH`).
* **Installed Version:** Phiên bản hiện tại đang cài trong dự án.
* **Fixed Version:** Phiên bản tối thiểu đã sửa lỗi mà bạn **BẮT BUỘC phải nâng cấp lên**.

---

### 6.2. 3 Bước xử lý triệt để cho Developer

#### Bước 1: Xác định thư viện và phiên bản an toàn
Nhìn vào cột **Fixed Version** trong bảng kết quả. (Ví dụ: `axios` cần nâng từ `0.21.1` lên `>= 1.6.0`).

#### Bước 2: Nâng cấp phiên bản trong file quản lý gói
* **NodeJS (npm/yarn):**
  ```bash
  npm install axios@latest
  # hoặc cập nhật package.json và chạy:
  npm update axios
  ```
* **Python (pip/requirements.txt):**
  Sửa trong `requirements.txt` thành phiên bản an toàn và chạy `pip install -r requirements.txt`.
* **Golang (go.mod):**
  ```bash
  go get -u github.com/gin-gonic/gin@v1.9.1
  go mod tidy
  ```
* **Java (Maven `pom.xml` / Gradle):**
  Nâng version của `<dependency>` trong file `pom.xml`.

#### Bước 3: Chạy lại Trivy để kiểm tra
```bash
trivy fs -s HIGH,CRITICAL --ignore-unfixed .
```
Nếu màn hình thông báo sạch không còn CVE thì bạn đã xử lý thành công!

---

### 6.3. Cách tạo file `.trivyignore` để loại trừ (False Positive / Rủi ro chấp nhận)

Nếu dự án bắt buộc phải dùng phiên bản thư viện cũ và rủi ro này đã được đội Security chấp thuận (Accepted Risk):

1. Tạo file `.trivyignore` tại thư mục gốc dự án:
   ```text
   # Bỏ qua CVE của axios vì tính năng này không được kích hoạt trong môi trường prod
   CVE-2023-45857

   # Bỏ qua lỗi prototype pollution đã có WAF chặn phía trước
   CVE-2022-24999
   ```

2. Khi Trivy quét, nó sẽ tự động đọc file `.trivyignore` và bỏ qua các CVE này.

---

## 7. BẢNG TRA CỨU NHANH LỆNH (CHEAT SHEET)

| Nhu cầu thao tác | Câu lệnh Terminal |
| :--- | :--- |
| **Quét nhanh thư mục mã nguồn hiện tại** | `trivy fs .` |
| **Chỉ quét lỗ hổng HIGH & CRITICAL có bản vá** | `trivy fs -s HIGH,CRITICAL --ignore-unfixed .` |
| **Quét một Docker Image cụ thể** | `trivy image nginx:alpine` |
| **Xuất danh mục phần mềm SBOM chuẩn CycloneDX** | `trivy fs --format cyclonedx -o sbom.json .` |
| **Xuất báo cáo dạng JSON chi tiết** | `trivy fs --format json -o report.json .` |
| **Chặn Pipeline (trả về Exit Code 1) nếu có lỗ hổng** | `trivy fs --exit-code 1 -s CRITICAL .` |
| **Chỉ tải trước DB mà không quét** | `trivy image --download-db-only` |
| **Xóa cache cơ sở dữ liệu Trivy trên máy** | `trivy clean --all` |

---

## 8. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING & FAQS)

### Q1: Tại sao bước `download-db-only` chạy rất chậm hoặc bị lỗi kết nối?
* **Nguyên nhân:** Trivy tải DB từ GitHub Container Registry (`ghcr.io`). Đôi khi mạng nội bộ hoặc DNS chặn kết nối.
* **Khắc phục:** Thêm cờ retry hoặc kiểm tra kết nối mạng:
  ```bash
  trivy image --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db:2
  ```

### Q2: Tại sao quét thư mục `fs` không tìm thấy lỗi dù thư viện rất cũ?
* **Nguyên nhân:** Trivy đọc thông tin phụ thuộc từ các file Lock (`package-lock.json`, `yarn.lock`, `go.sum`, `poetry.lock`, `pom.xml`). Nếu bạn chỉ có code thô mà chưa từng chạy `npm install` để sinh file lock, Trivy sẽ không thể phân tích cây phụ thuộc đầy đủ.
* **Khắc phục:** Đảm bảo file lock đã được sinh ra và commit vào repository.

### Q3: File SBOM `result1.json` được gửi lên Dependency-Track để làm gì?
* **Trả lời:** Dependency-Track là nền tảng quản lý rủi ro chuỗi cung ứng phần mềm. Khi có một lỗ hổng zero-day mới được phát hiện trên toàn cầu, Dependency-Track sẽ lập tức tra cứu trong database xem service nào của FTECH đang dùng thư viện đó và cảnh báo cho đội bảo mật mà không cần phải chạy lại toàn bộ CI Pipeline.
