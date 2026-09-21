# HƯỚNG DẪN TOÀN DIỆN VỀ SONARQUBE CHO LẬP TRÌNH VIÊN & DEVSECOPS

> **Tài liệu hướng dẫn thực hành DevSecOps:** Được tổng hợp và đối chiếu từ:
> 1. **Tài liệu mã nguồn mở chính thức của SonarSource SonarQube** (phân tích tĩnh SAST, chất lượng mã nguồn, đo lường nợ kỹ thuật, Quality Gate).
> 2. **Hiện trạng cấu hình thực tế tại FTECH** (được đối chiếu từ job `sonarqube-check` trong `CI/devsecops-template.yml`, `CI/README.MD` và `MÔ HÌNH HỆ THỐNG CI_CD CỦA CÔNG TY FTECH.md`).

---

## MỤC LỤC

1. [Tổng quan về SonarQube & Phân tích Tĩnh (SAST & Code Quality)](#1-tổng-quan-về-sonarqube--phân-tích-tĩnh-sast--code-quality)
   - 1.1. SonarQube là gì?
   - 1.2. Vị trí của SonarQube trong DevSecOps: SAST vs SCA vs Secret Scanning
   - 1.3. 4 Trụ cột phân tích: Bugs, Vulnerabilities, Security Hotspots, Code Smells
   - 1.4. Triết lý "Clean Code" & "Clean as You Code" (CaYC)
   - 1.5. Nợ kỹ thuật (Technical Debt) & Thang đo xếp hạng SQALE (A -> E)
2. [Kiến trúc & Cài đặt Môi trường Local](#2-kiến-trúc--cài-đặt-môi-trường-local)
   - 2.1. Kiến trúc hệ thống SonarQube
   - 2.2. Khởi chạy nhanh SonarQube Server cục bộ bằng Docker
   - 2.3. Cài đặt SonarScanner CLI trên máy cá nhân (Windows / macOS / Linux)
   - 2.4. Cài đặt & kết nối SonarLint trên IDE (Shift-Left Security)
3. [Cấu hình Phân tích Mã nguồn (`sonar-project.properties`)](#3-cấu-hình-phân-tích-mã-nguồn-sonar-projectproperties)
   - 3.1. Cấu trúc file `sonar-project.properties` chuẩn
   - 3.2. Bảng tham số cốt lõi (`sonar.projectKey`, `sonar.sources`, `sonar.exclusions`,...)
   - 3.3. Tích hợp báo cáo Unit Test & Code Coverage đa ngôn ngữ
4. [Hướng dẫn Quét theo từng Hệ sinh thái Ngôn ngữ](#4-hướng-dẫn-quét-theo-từng-hệ-sinh-thái-ngôn-ngữ)
   - 4.1. SonarScanner CLI (Dự án tổng hợp, Frontend JS/TS, Python, Go, PHP)
   - 4.2. Java với Maven (`mvn sonar:sonar`)
   - 4.3. Java với Gradle (`gradle sonar`)
   - 4.4. .NET / C# (`dotnet sonarscanner`)
5. [Bộ tiêu chuẩn Đánh giá: Quality Profiles & Quality Gates](#5-bộ-tiêu-chuẩn-đánh-giá-quality-profiles--quality-gates)
   - 5.1. Quality Profile: Bộ quy tắc phân tích (Ruleset)
   - 5.2. Quality Gate: Cổng kiểm soát chất lượng phần mềm
   - 5.3. Khái niệm "New Code Period" - Trọng tâm của Clean as You Code
   - 5.4. Quy trình rà soát Security Hotspots
6. [Phân tích Cấu hình THỰC TẾ tại FTECH (`devsecops-template.yml`)](#6-phân-tích-cấu-hình-thực-tế-tại-ftech-devsecops-templateyml)
   - 6.1. Job `sonarqube-check` trong Pipeline FTECH
   - 6.2. Phân tích chi tiết từng biến môi trường (`SONAR_HOST_URL`, `GIT_DEPTH`, `SONAR_USER_HOME`,...)
   - 6.3. Cơ chế Caching thư mục `.sonar/cache`
   - 6.4. Thiết lập biến môi trường bắt buộc trên GitLab CI (*Settings > CI/CD > Variables*)
   - 6.5. Đánh giá chính sách bảo mật (`allow_failure: true` vs `allow_failure: false`)
7. [Quy trình Xử lý cho Lập trình viên (Developer Remediation Guide)](#7-quy-trình-xử-lý-cho-lập-trình-viên-developer-remediation-guide)
   - 7.1. Cách đọc bảng điều khiển SonarQube & lần theo vết lỗi
   - 7.2. 4 Bước khắc phục Bug / Vulnerability / Hotspot
   - 7.3. Cách loại trừ ngoại lệ trong mã nguồn (`// NOSONAR`, `@SuppressWarnings`)
   - 7.4. Đánh dấu False Positive / Won't Fix trên giao diện Web UI
8. [Bảng tra cứu nhanh tham số & lệnh (Cheat Sheet)](#8-bảng-tra-cứu-nhanh-tham-số--lệnh-cheat-sheet)
9. [Xử lý sự cố thường gặp (Troubleshooting & FAQs)](#9-xử-lý-sự-cố-thường-gặp-troubleshooting--faqs)

---

## 1. TỔNG QUAN VỀ SONARQUBE & PHÂN TÍCH TĨNH (SAST & CODE QUALITY)

### 1.1. SonarQube là gì?
**SonarQube** (do SonarSource phát triển) là nền tảng kiểm tra tự động mã nguồn mở hàng đầu thế giới, chuyên dùng để thực hiện **Kiểm thử Bảo mật Tĩnh (Static Application Security Testing - SAST)** và **Đo lường Chất lượng Mã nguồn (Code Quality & Maintainability)** cho hơn 30+ ngôn ngữ lập trình.

SonarQube giúp các đội ngũ phát triển phần mềm phát hiện sớm các lỗi tiềm ẩn, lỗ hổng an ninh, mã nguồn trùng lặp và sự suy giảm cấu trúc trước khi code được triển khai lên môi trường Production.

---

### 1.2. Vị trí của SonarQube trong DevSecOps: SAST vs SCA vs Secret Scanning

Trong mô hình kiểm thử bảo mật toàn diện của FTECH, 3 công cụ phối hợp chặt chẽ ở các tầng khác nhau:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 HỆ THỐNG DEVSECOPS PIPELINE FTECH                                │
├──────────────────────────┬──────────────────────────────────────┬────────────────────────────────┤
│      DETECT-SECRETS      │             AQUA TRIVY               │           SONARQUBE            │
│   (Secret Scanning)      │      (SCA & Vulnerabilities)         │      (SAST & Code Quality)     │
├──────────────────────────┼──────────────────────────────────────┼────────────────────────────────┤
│ 🎯 Quét thông tin nhạy   │ 🎯 Quét mã nguồn mở & thư viện       │ 🎯 Phân tích trực tiếp mã      │
│    cảm bị hard-code      │    bên thứ ba (3rd party dependencies│    nguồn dự án do lập trình    │
│    (API Key, Password,   │    như npm, pip, maven, nuget, golang│    viên công ty tự viết        │
│    Private Key, JWT...)  │    hoặc OS base images).             │    (Application Source Code).  │
├──────────────────────────┼──────────────────────────────────────┼────────────────────────────────┤
│ 🔍 Cơ chế: Regex,        │ 🔍 Cơ chế: Đối chiếu file lock       │ 🔍 Cơ chế: Phân tích cú pháp   │
│    Shannon Entropy.      │    với cơ sở dữ liệu CVE toàn cầu.   │    AST, luồng dữ liệu Taint.   │
├──────────────────────────┼──────────────────────────────────────┼────────────────────────────────┤
│ 🛑 Output: Chặn commit / │ 📦 Output: File SBOM CycloneDX       │ 📊 Output: Dashboard chất lượng│
│    pipeline tức thì.     │    đẩy lên OWASP Dependency-Track.   │    & đánh giá Quality Gate.    │
└──────────────────────────┴──────────────────────────────────────┴────────────────────────────────┘
```

---

### 1.3. 4 Trụ cột phân tích: Bugs, Vulnerabilities, Security Hotspots, Code Smells

SonarQube phân loại tất cả các vấn đề phát hiện được vào 4 danh mục chuẩn:

```
                                  ┌──────────────────────────────┐
                                  │      KẾT QUẢ PHÂN TÍCH       │
                                  └──────────────┬───────────────┘
                 ┌───────────────────────────────┼───────────────────────────────┐
                 │                               │                               │
                 ▼                               ▼                               ▼
       ┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
       │   ĐỘ TIN CẬY     │            │    BẢO MẬT       │            │   KHẢ NĂNG BẢO TRÌ│
       │  (Reliability)   │            │    (Security)    │            │ (Maintainability)│
       └─────────┬────────┘            └────────┬─────────┘            └────────┬─────────┘
                 │                              │                               │
                 ▼                       ┌──────┴──────┐                        ▼
          ┌─────────────┐                │             │                 ┌─────────────┐
          │    BUGS     │                ▼             ▼                 │ CODE SMELLS │
          └─────────────┘        ┌─────────────┐ ┌─────────────┐         └─────────────┘
                                 │VULNERABILITY│ │  SECURITY   │
                                 │             │ │   HOTSPOT   │
                                 └─────────────┘ └─────────────┘
```

| Danh mục | Định nghĩa | Mức độ tác động | Ví dụ điển hình |
| :--- | :--- | :--- | :--- |
| 🐛 **Bug** | Lỗi logic trong code có nguy cơ cao dẫn đến crash chương trình hoặc hành vi sai lệch trong runtime. | Làm gián đoạn dịch vụ, hỏng dữ liệu | `NullPointerException`, vòng lặp vô tận, so sánh chuỗi bằng `==` trong Java. |
| 🔓 **Vulnerability** | Lỗ hổng bảo mật rõ ràng đã được xác định, có thể bị kẻ tấn công khai thác trực tiếp. | Rò rỉ dữ liệu, RCE, chiếm quyền | SQL Injection, XSS, Path Traversal, Hard-coded cryptographic key. |
| 🛡️ **Security Hotspot** | Đoạn mã nhạy cảm về an ninh **cần con người vào review thủ công** để xác định xem ngữ cảnh sử dụng có an toàn hay không. | Tiềm ẩn rủi ro nếu cấu hình sai | Dùng thuật toán băm yếu (`MD5`, `SHA1`), tắt xác thực SSL/TLS, cấu hình CORS `*`. |
| 🦨 **Code Smell** | Vấn đề về thiết kế code, vi phạm chuẩn clean code, khiến dự án khó đọc, khó bảo trì và dễ sinh bug sau này. | Làm tăng Technical Debt, giảm tốc độ dev | Hàm dài 500 dòng, độ phức tạp Cyclomatic quá cao, code trùng lặp, biến không sử dụng. |

---

### 1.4. Triết lý "Clean Code" & "Clean as You Code" (CaYC)

SonarQube đưa ra phương pháp luận hiện đại **Clean as You Code**:
* **Không tốn công sức dọn sạch toàn bộ mã nguồn cũ (Legacy Code) trong một sớm một chiều:** Việc dọn sạch hàng triệu dòng code cũ thường bất khả thi và rủi ro cao.
* **Tập trung giữ cho "Code Mới" (New Code) luôn sạch:** Bất kỳ đoạn code nào được viết mới hoặc sửa đổi trong nhánh hiện tại (Pull/Merge Request) **phải đáp ứng 100% tiêu chuẩn chất lượng**.
* **Kết quả dài hạn:** Chất lượng codebase sẽ tự động tăng dần theo thời gian một cách tự nhiên mà không làm chậm tiến độ bàn giao tính năng.

---

### 1.5. Nợ kỹ thuật (Technical Debt) & Thang đo xếp hạng SQALE (A -> E)

SonarQube tự động ước tính **thời gian (phút/giờ/ngày)** cần thiết để lập trình viên sửa sạch các Code Smell và gán nhãn xếp hạng từ **A** đến **E**:

* 🟢 **Độ xếp hạng A (Tuyệt vời):** Nợ kỹ thuật $\le 5\%$ tổng thời gian phát triển dự án.
* 🟡 **Độ xếp hạng B (Tốt):** Nợ kỹ thuật từ $6\% - 10\%$.
* 🟠 **Độ xếp hạng C (Trung bình):** Nợ kỹ thuật từ $11\% - 20\%$.
* 🔴 **Độ xếp hạng D (Kém):** Nợ kỹ thuật từ $21\% - 50\%$.
* ⛔ **Độ xếp hạng E (Rất kém):** Nợ kỹ thuật $> 50\%$.

---

## 2. KIẾN TRÚC & CÀI ĐẶT MÔI TRƯỜNG LOCAL

### 2.1. Kiến trúc hệ thống SonarQube

Kiến trúc SonarQube bao gồm 3 thành phần chính hoạt động phối hợp:

```
 ┌────────────────────────────────────────────────────────┐
 │                      DEVELOPER                         │
 │     IDE (VS Code / IntelliJ) + SonarLint Extension     │
 └──────────────────────────┬─────────────────────────────┘
                            │ (1) Push Code / Merge Request
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │                   GITLAB CI RUNNER                     │
 │          Job: sonarsource/sonar-scanner-cli            │
 └──────────────────────────┬─────────────────────────────┘
                            │ (2) Tải Source + Phân tích AST + Gửi Report
                            ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                    SONARQUBE SERVER (FTECH ENTERPRISE)                   │
 │                URL: https://sonarqube.dev.ftech.ai                       │
 │ ┌───────────────────┐ ┌───────────────────┐ ┌──────────────────────────┐ │
 │ │    Web Server     │ │ Compute Engine    │ │  Search Engine           │ │
 │ │ (UI Dashboard API)│ │(Xử lý Report/Gate)│ │  (ElasticSearch Index)   │ │
 │ └─────────┬─────────┘ └─────────┬─────────┘ └────────────┬─────────────┘ │
 └───────────┼─────────────────────┼────────────────────────┼───────────────┘
             └─────────────────────┼────────────────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │    PostgreSQL Database        │
                   │ (Lưu Project, Rules, History) │
                   └───────────────────────────────┘
```

---

### 2.2. Khởi chạy nhanh SonarQube Server cục bộ bằng Docker

Nếu muốn thử nghiệm hoặc kiểm thử nội bộ trên máy cá nhân trước khi kết nối lên server FTECH:

```bash
# Chạy SonarQube Community Edition bản mới nhất
docker run -d --name sonarqube-local \
  -p 9000:9000 \
  -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true \
  sonarqube:community
```

Truy cập: `http://localhost:9000` (Tài khoản mặc định: `admin` / `admin`).

---

### 2.3. Cài đặt SonarScanner CLI trên máy cá nhân

#### Trên macOS (Homebrew):
```bash
brew install sonar-scanner
```

#### Trên Linux (Ubuntu/Debian):
```bash
wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip
unzip sonar-scanner-cli-5.0.1.3006-linux.zip
sudo mv sonar-scanner-5.0.1.3006-linux /opt/sonar-scanner
export PATH=$PATH:/opt/sonar-scanner/bin
```

#### Trên Windows (Winget hoặc Chocolatey):
```powershell
choco install sonar-scanner-msbuild
# Hoặc tải file zip chính thức từ SonarSource và thêm vào biến môi trường PATH
```

#### Chạy nhanh qua Docker (Không cần cài đặt CLI vào máy):
```bash
docker run --rm \
  -e SONAR_HOST_URL="https://sonarqube.dev.ftech.ai" \
  -e SONAR_TOKEN="sqp_your_token_here" \
  -v "$(pwd):/usr/src" \
  sonarsource/sonar-scanner-cli:latest \
  -Dsonar.projectKey=my-project-key
```

---

### 2.4. Cài đặt & kết nối SonarLint trên IDE (Shift-Left Security)

> [!TIP]
> **SonarLint** là plugin cài trực tiếp vào Visual Studio Code hoặc IntelliJ IDEA. Nó hoạt động như một "lỗi chính tả code", cảnh báo Bug, Security Hotspot và Code Smell **ngay trong lúc bạn đang gõ từng dòng code**, giúp loại bỏ lỗi trước khi commit lên Git.

#### Cấu hình "Connected Mode" với SonarQube Server FTECH:
1. Cài đặt extension **SonarLint** từ VS Code Marketplace / JetBrains Plugins.
2. Mở Settings của SonarLint và liên kết tới Server FTECH:
   - **Server URL:** `https://sonarqube.dev.ftech.ai`
   - **User Token:** Tạo tại *SonarQube Server > My Account > Security > Generate Token*.
   - **Project Key:** Khóa dự án tương ứng.
3. Khi lập trình, SonarLint sẽ tự động đồng bộ đúng bộ quy tắc (Quality Profile) từ server FTECH về máy cá nhân!

---

## 3. CẤU HÌNH PHÂN TÍCH MÃ NGUỒN (`sonar-project.properties`)

### 3.1. Cấu trúc file `sonar-project.properties` chuẩn

Nên đặt file `sonar-project.properties` tại thư mục gốc của repository để cấu hình tường minh phạm vi phân tích:

```properties
# ==========================================
# 1. ĐỊNH DANH DỰ ÁN TRÊN SONARQUBE SERVER
# ==========================================
sonar.projectKey=ftech-payment-service
sonar.projectName=FTECH Payment Microservice
sonar.projectVersion=1.0.0

# ==========================================
# 2. PHẠM VI MÃ NGUỒN VÀ KIỂM THỬ
# ==========================================
sonar.sources=src
sonar.tests=tests
sonar.sourceEncoding=UTF-8

# ==========================================
# 3. DANH SÁCH LOẠI TRỪ (EXCLUSIONS)
# ==========================================
# Loại trừ code sinh tự động, thư viện bên thứ 3 và build artifacts
sonar.exclusions=**/node_modules/**,**/vendor/**,**/dist/**,**/build/**,**/*.spec.ts,**/*.test.js,**/generated/**

# Loại trừ file không cần tính độ phủ kiểm thử (Code Coverage)
sonar.coverage.exclusions=**/tests/**,**/*.mock.ts,**/config/**,**/migrations/**

# ==========================================
# 4. BÁO CÁO UNIT TEST & COVERAGE REPORTS
# ==========================================
# Ví dụ cho dự án TypeScript / NodeJS:
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.testExecutionReportPaths=test-report.xml
```

---

### 3.2. Bảng tham số cốt lõi

| Tham số | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- |
| **`sonar.projectKey`** | Mã định danh duy nhất của dự án trên SonarQube Server (Bắt buộc). | `ftech_core_api` |
| **`sonar.sources`** | Danh sách thư mục chứa mã nguồn cần quét (phân cách bằng dấu phẩy). | `src,lib,app` |
| **`sonar.tests`** | Danh sách thư mục chứa code Unit Test (để SonarQube không quét lỗi maintainability trên test). | `test,spec` |
| **`sonar.exclusions`** | Mẫu đường dẫn các file/thư mục **bỏ qua hoàn toàn** không phân tích. | `**/vendor/**,**/dist/**` |
| **`sonar.inclusions`** | Chỉ định đích danh các file cần phân tích (ngược lại với exclusions). | `src/**/*.ts` |
| **`sonar.qualitygate.wait`** | Chờ (`true`) hay không chờ (`false`) kết quả Quality Gate trước khi kết thúc pipeline. | `true` |
| **`sonar.token`** / **`SONAR_TOKEN`** | Mã Token xác thực quyền đẩy kết quả lên SonarQube. | `sqp_xxxxxx` |

---

### 3.3. Tích hợp báo cáo Unit Test & Code Coverage đa ngôn ngữ

SonarQube không tự chạy unit test mà đọc kết quả từ các file report do test runner sinh ra:

| Ngôn ngữ | Test Tool phổ biến | Tham số cấu hình SonarQube |
| :--- | :--- | :--- |
| **JavaScript / TypeScript** | Jest, Mocha, Karma (lcov) | `sonar.javascript.lcov.reportPaths=coverage/lcov.info` |
| **Python** | pytest-cov, coverage.py (xml) | `sonar.python.coverage.reportPaths=coverage.xml` |
| **Java** | JaCoCo, Surefire | `sonar.coverage.jacoco.xmlReportPaths=build/reports/jacoco/test/jacocoTestReport.xml` |
| **Golang** | `go test -coverprofile` | `sonar.go.coverage.reportPaths=coverage.out` |
| **PHP** | PHPUnit (clover) | `sonar.php.coverage.reportPaths=coverage.xml` |
| **.NET / C#** | Coverlet, OpenCover | `sonar.cs.opencover.reportsPaths=**/coverage.opencover.xml` |

---

## 4. HƯỚNG DẪN QUÉT THEO TỪNG HỆ SINH THÁI NGÔN NGỮ

### 4.1. SonarScanner CLI (NodeJS / Frontend / Python / Go)

Dùng cho các dự án đa ngôn ngữ hoặc không dùng build tool như Maven/Gradle:

```bash
sonar-scanner \
  -Dsonar.host.url=https://sonarqube.dev.ftech.ai \
  -Dsonar.token=$SONAR_TOKEN \
  -Dsonar.projectKey=$SONAR_PROJECT_KEY \
  -Dsonar.sources=. \
  -Dsonar.exclusions="**/node_modules/**,**/dist/**"
```

---

### 4.2. Java với Maven

Maven có sẵn plugin chính thức từ SonarSource. Bạn không cần cài `sonar-scanner-cli`:

```bash
# Chạy Unit Test sinh JaCoCo report và phân tích SonarQube trong 1 lệnh:
mvn clean verify sonar:sonar \
  -Dsonar.host.url=https://sonarqube.dev.ftech.ai \
  -Dsonar.token=$SONAR_TOKEN \
  -Dsonar.projectKey=$SONAR_PROJECT_KEY
```

---

### 4.3. Java với Gradle

Trong file `build.gradle`:

```groovy
plugins {
    id "org.sonarqube" version "4.4.1.3373"
    id "jacoco"
}

sonar {
    properties {
        property "sonar.projectKey", "ftech-gradle-service"
        property "sonar.host.url", "https://sonarqube.dev.ftech.ai"
        property "sonar.coverage.jacoco.xmlReportPaths", "build/reports/jacoco/test/jacocoTestReport.xml"
    }
}
```

Thực thi lệnh quét:
```bash
./gradlew test jacocoTestReport sonar -Dsonar.token=$SONAR_TOKEN
```

---

### 4.4. .NET / C#

```powershell
# 1. Bắt đầu phiên quét
dotnet-sonarscanner begin \
  /k:"$SONAR_PROJECT_KEY" \
  /d:sonar.host.url="https://sonarqube.dev.ftech.ai" \
  /d:sonar.token="$SONAR_TOKEN" \
  /d:sonar.cs.opencover.reportsPaths="**/coverage.opencover.xml"

# 2. Build dự án & Chạy Unit Test
dotnet build
dotnet test --collect:"XPlat Code Coverage"

# 3. Kết thúc phiên quét và đẩy dữ liệu lên server
dotnet-sonarscanner end /d:sonar.token="$SONAR_TOKEN"
```

---

## 5. BỘ TIÊU CHUẨN ĐÁNH GIÁ: QUALITY PROFILES & QUALITY GATES

### 5.1. Quality Profile: Bộ quy tắc phân tích (Ruleset)

* **Quality Profile** tập hợp tất cả các quy tắc (Rules) được áp dụng khi phân tích một ngôn ngữ cụ thể (ví dụ: Sonar way cho Java, Sonar way cho TypeScript).
* Mỗi Rule có mức độ nghiêm trọng:
  - 🔴 **Blocker:** Lỗi chết người, bắt buộc sửa ngay.
  - 🟠 **Critical:** Rất nguy hiểm, nguy cơ cao gây crash hoặc thủng bảo mật.
  - 🟡 **Major:** Lỗi ảnh hưởng chất lượng mã nguồn.
  - 🔵 **Minor:** Lỗi nhỏ, vi phạm chuẩn style code.
  - ⚪ **Info:** Thông tin tham khảo.

---

### 5.2. Quality Gate: Cổng kiểm soát chất lượng phần mềm

**Quality Gate** là tập hợp các điều kiện Boolean (Đạt / Không đạt) quyết định xem một bản build mã nguồn có đủ tiêu chuẩn để chuyển sang bước tiếp theo hay không:

```
                               ┌──────────────────────────────┐
                               │     KẾT QUẢ PHÂN TÍCH        │
                               └──────────────┬───────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │       KIỂM TRA QUALITY GATE     │
                             │  • New Bugs = 0                 │
                             │  • New Vulnerabilities = 0      │
                             │  • Security Hotspots = 100% Rev │
                             │  • Coverage on New Code ≥ 80%   │
                             │  • Duplicated Lines on New ≤ 3% │
                             └────────┬───────────────┬────────┘
                                      │               │
                            [TẤT CẢ ĐIỀU KIỆN ĐẠT]    [CÓ ĐIỀU KIỆN VI PHẠM]
                                      │               │
                                      ▼               ▼
                                🟢 PASSED           🔴 FAILED
                               (Cho phép Merge)    (Chặn Pipeline)
```

---

### 5.3. Khái niệm "New Code Period" - Trọng tâm của Clean as You Code

SonarQube định nghĩa **New Code (Mã nguồn mới)** dựa trên 1 trong các tiêu chí:
1. **Previous Version:** Code thay đổi so với phiên bản release trước.
2. **Number of Days:** Code thay đổi trong vòng $X$ ngày gần nhất (mặc định 30 ngày).
3. **Reference Branch:** Code thay đổi so với nhánh chính (`main` / `master` / `develop`) — **Phương pháp chuẩn nhất cho luồng Merge Request tại FTECH**.

---

### 5.4. Quy trình rà soát Security Hotspots

Khi SonarQube đánh dấu một vị trí là Security Hotspot, lập trình viên và Security Lead thực hiện rà soát theo vòng đời:

```
  [TO REVIEW] ──► Chuyên gia / DevLead mở giao diện SonarQube kiểm tra ngữ cảnh
        │
        ├──► [ACKNOWLEDGED] : Xác nhận rủi ro nhưng chấp nhận để lại
        ├──► [FIXED]        : Đã chỉnh sửa code để an toàn tuyệt đối
        └──► [SAFE]         : Ngữ cảnh an toàn, đoạn code không thể bị khai thác
```

---

## 6. PHÂN TÍCH CẤU HÌNH THỰC TẾ TẠI FTECH (`devsecops-template.yml`)

### 6.1. Job `sonarqube-check` trong Pipeline FTECH

Trích đoạn cấu hình từ file template dùng chung toàn công ty ([devsecops-template.yml](file:///d:/FTECH/CI-CD/CI/devsecops-template.yml)):

```yaml
sonarqube-check:
  stage: sonarqube-check
  image:
    name: sonarsource/sonar-scanner-cli:latest
    entrypoint: [""]
  variables:
    SONAR_USER_HOME: "${CI_PROJECT_DIR}/.sonar"
    GIT_DEPTH: "0"
    SONAR_HOST_URL: "https://sonarqube.dev.ftech.ai"
  cache:
    key: "${CI_JOB_NAME}"
    paths:
      - .sonar/cache
  script:
    - sonar-scanner -Dsonar.projectKey=$SONAR_PROJECT_KEY -Dsonar.qualitygate.wait=$SONAR_QUALITYGATE_WAIT
  tags: [devsecops]
  allow_failure: true
```

---

### 6.2. Phân tích chi tiết từng tham số & biến môi trường

#### 1. `image: sonarsource/sonar-scanner-cli:latest` & `entrypoint: [""]`
* Sử dụng image chính thức từ SonarSource chứa sẵn công cụ `sonar-scanner` và môi trường chạy Java runtime.
* Cần ghi đè `entrypoint: [""]` để GitLab Runner có thể gọi các shell script tự do bên trong container.

#### 2. `GIT_DEPTH: "0"` (VÔ CÙNG QUAN TRỌNG)
* **Ý nghĩa:** Mặc định GitLab CI chỉ clone nông (shallow clone với depth = 50 hoặc 20 commits). Gán `GIT_DEPTH: "0"` ép buộc Runner **clone toàn bộ lịch sử Git của repository**.
* **Tại sao bắt buộc?** SonarQube cần toàn bộ thông tin `git blame` (ai sửa dòng nào, vào thời điểm nào) để:
  - Xác định chính xác đoạn nào là **New Code**.
  - Tự động gán lỗi (Auto-assign Issue) cho đúng lập trình viên đã commit dòng code đó.

#### 3. `SONAR_HOST_URL: "https://sonarqube.dev.ftech.ai"`
* Trỏ trực tiếp đến máy chủ SonarQube Server nội bộ của FTECH.

#### 4. `SONAR_USER_HOME: "${CI_PROJECT_DIR}/.sonar"`
* Chỉ định thư mục làm việc và lưu cache của SonarScanner nằm ngay trong workspace dự án để GitLab Runner có thể truy cập và nén cache.

---

### 6.3. Cơ chế Caching thư mục `.sonar/cache`

```yaml
cache:
  key: "${CI_JOB_NAME}"
  paths:
    - .sonar/cache
```

* **Cơ chế:** Lần chạy đầu tiên, SonarScanner tải các bộ rules, plugins từ Server về thư mục `.sonar/cache`. Runner sẽ lưu thư mục này lại.
* **Hiệu quả:** Ở các lần chạy pipeline tiếp theo, scanner không cần tải lại hàng trăm MB dữ liệu ruleset từ server `sonarqube.dev.ftech.ai`, giúp rút ngắn thời gian chạy job từ vài phút xuống còn vài chục giây.

---

### 6.4. Thiết lập biến môi trường bắt buộc trên GitLab CI

Để job `sonarqube-check` chạy thành công, lập trình viên/DevSecOps cần khai báo các biến sau tại **Settings > CI/CD > Variables** của repository:

| Tên biến | Loại | Masked? | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| **`SONAR_PROJECT_KEY`** | Variable | ❌ Không | Khóa định danh của dự án trên `https://sonarqube.dev.ftech.ai` (ví dụ: `my-project-api`). |
| **`SONAR_TOKEN`** | Variable | ✅ Có | Token xác thực tạo từ tài khoản SonarQube có quyền đẩy report lên project. |
| **`SONAR_QUALITYGATE_WAIT`** | Variable | ❌ Không | Gán `true` nếu muốn job đợi kiểm tra Quality Gate, hoặc `false` nếu chỉ đẩy dữ liệu lên mà không đợi. |

---

### 6.5. Đánh giá chính sách bảo mật (`allow_failure: true` vs `false`)

> [!NOTE]
> * Trong cấu hình hiện tại của FTECH, job `sonarqube-check` được gán **`allow_failure: true`** (Soft Gate).
> * **Lợi ích:** Tránh làm nghẽn tiến độ phát hành khi dự án có các Code Smell hoặc vi phạm nhẹ.
> * **Khuyến nghị lộ trình nâng cấp (Hard Gate):**
>   - Nhánh `feature/*` hoặc `dev`: Giữ `allow_failure: true` để tạo môi trường linh hoạt cho lập trình viên sửa dần.
>   - Nhánh `main`, `master`, `prod` (hoặc các Merge Request vào nhánh chính): Đặt `allow_failure: false` để đảm bảo code lên môi trường Production tuyệt đối không dính lỗi Blocker/Critical nào!

---

## 7. QUY TRÌNH XỬ LÝ CHO LẬP TRÌNH VIÊN (DEVELOPER REMEDIATION GUIDE)

### 7.1. Cách đọc bảng điều khiển SonarQube & lần theo vết lỗi

Khi job hoàn thành, mở đường dẫn SonarQube được in trong log console:

```text
INFO: ANALYSIS SUCCESSFUL, you can find the results at: https://sonarqube.dev.ftech.ai/dashboard?id=my-project-api
INFO: Note that you will be able to access the updated dashboard once the server has processed the submitted analysis report
INFO: More about the report processing at https://sonarqube.dev.ftech.ai/api/ce/task?id=AY...
INFO: Quality Gate status: PASSED
```

1. **Dashboard Tổng quan:** Xem trạng thái Quality Gate (**PASSED** màu xanh hoặc **FAILED** màu đỏ).
2. **Tab Issues:** Lọc theo Type (`Bug`, `Vulnerability`, `Code Smell`) và Severity (`Blocker`, `Critical`).
3. **Xem Chi tiết Dòng Code:** Nhấp vào từng Issue, SonarQube sẽ chỉ rõ:
   - Dòng code vi phạm.
   - Giải thích lý do tại sao dòng code này nguy hiểm (*Why is this an issue?*).
   - Hướng dẫn cách sửa mã chuẩn (*How can I fix it?*).

---

### 7.2. 4 Bước khắc phục Bug / Vulnerability / Hotspot

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Bước 1: Tra cứu │ ──► │ Bước 2: Sửa mã  │ ──► │ Bước 3: Kiểm tra│ ──► │ Bước 4: Commit  │
│ vị trí & gợi ý  │     │ nguồn tại Local │     │ lại bằng Sonar- │     │ và theo dõi     │
│ sửa trên Web UI │     │ theo chuẩn Clean│     │ Lint / Scanner  │     │ lại trên GitLab │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Bước 1: Tra cứu chi tiết:** Đọc giải thích và đoạn mã mẫu an toàn mà SonarQube gợi ý.
2. **Bước 2: Sửa mã nguồn:** Áp dụng các mẫu thiết kế an toàn (Parameterized Query thay vì cộng chuỗi SQL, dùng `Optional` hoặc kiểm tra null đầy đủ).
3. **Bước 3: Kiểm tra cục bộ:** Sử dụng SonarLint trên IDE để xác nhận cảnh báo đã biến mất.
4. **Bước 4: Push code:** Đẩy commit mới lên GitLab, theo dõi job `sonarqube-check` chuyển sang trạng thái xanh.

---

### 7.3. Cách loại trừ ngoại lệ trong mã nguồn

Trong trường hợp đoạn code là chủ đích thiết kế hoặc là trường hợp đặc biệt không thể refactor ngay:

#### 1. Sử dụng comment inline `// NOSONAR`
Đặt ở cuối dòng mã nguồn để yêu cầu SonarQube bỏ qua tất cả các rule trên dòng đó:

```javascript
// Bỏ qua cảnh báo trên dòng này
const secretKey = "hardcoded_for_mock_testing_only"; // NOSONAR
```

#### 2. Sử dụng Java `@SuppressWarnings`
```java
@SuppressWarnings("java:S2068") // Tắt cảnh báo mã S2068 (Hard-coded password)
public void testMockAuthentication() {
    String testPassword = "admin_password";
}
```

#### 3. Loại trừ qua file cấu hình `sonar-project.properties`
```properties
# Bỏ qua hoàn toàn phân tích trên thư mục fixtures/mock
sonar.exclusions=src/mocks/**,tests/**
```

---

### 7.4. Đánh dấu False Positive / Won't Fix trên giao diện Web UI

Nếu cảnh báo là nhận diện sai (False Positive) hoặc rủi ro đã được chấp nhận (Won't Fix / Accept Risk):

1. Truy cập vào Issue cụ thể trên giao diện Web SonarQube (`https://sonarqube.dev.ftech.ai`).
2. Nhấp vào nút trạng thái của Issue (mặc định là **Open**).
3. Chọn một trong hai tùy chọn:
   - **False Positive:** Khẳng định phân tích của SonarQube bị nhầm lẫn trong trường hợp này.
   - **Accept Risk (Won't Fix):** Xác nhận có vi phạm nhưng đội ngũ phát triển chủ động chấp nhận rủi ro kỹ thuật.
4. Nhập lời giải thích rõ ràng và nhấn **Confirm**. Issue sẽ lập tức không còn tính vào Quality Gate nữa.

---

## 8. BẢNG TRA CỨU NHANH THAM SỐ & LỆNH (CHEAT SHEET)

| Nhu cầu thao tác | Câu lệnh / Tham số cấu hình |
| :--- | :--- |
| **Quét nhanh dự án hiện tại qua CLI** | `sonar-scanner -Dsonar.projectKey=my-app -Dsonar.host.url=https://sonarqube.dev.ftech.ai -Dsonar.token=$SONAR_TOKEN` |
| **Quét và chờ kết quả Quality Gate** | `sonar-scanner -Dsonar.projectKey=my-app -Dsonar.qualitygate.wait=true` |
| **Chỉ định thư mục mã nguồn và test** | `-Dsonar.sources=src -Dsonar.tests=tests` |
| **Loại trừ thư mục khỏi phân tích** | `-Dsonar.exclusions="**/dist/**,**/node_modules/**"` |
| **Bỏ qua kiểm tra độ phủ kiểm thử** | `-Dsonar.coverage.exclusions="**/*.test.ts,**/mock/**"` |
| **Quét dự án Maven** | `mvn clean verify sonar:sonar -Dsonar.token=$SONAR_TOKEN` |
| **Quét dự án Gradle** | `./gradlew sonar -Dsonar.token=$SONAR_TOKEN` |
| **Bật chế độ Debug chi tiết khi gặp lỗi** | `sonar-scanner -X` hoặc `sonar-scanner --debug` |
| **Xóa bộ nhớ đệm scanner trên máy** | `rm -rf .sonar/cache` (Linux/macOS) hoặc xóa `%USERPROFILE%\.sonar\cache` (Windows) |

---

## 9. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING & FAQS)

### Q1: Tại sao SonarQube báo lỗi `Shallow clone detected` hoặc không hiển thị tác giả dòng code (Git Blame)?
* **Nguyên nhân:** GitLab CI chỉ clone một số commit gần nhất (Shallow clone) khiến scanner không có đủ lịch sử Git để phân tích Blame và New Code.
* **Cách khắc phục:** Đảm bảo biến `GIT_DEPTH: "0"` đã được khai báo trong khối `variables` của job `sonarqube-check` như cấu hình chuẩn FTECH.

---

### Q2: Gặp lỗi `ERROR: You're not authorized to run analysis. Please contact the project administrator.`?
* **Nguyên nhân:** Biến `SONAR_TOKEN` chưa được cấu hình, token đã hết hạn, hoặc tài khoản tạo token không có quyền **Execute Analysis** trên project đó.
* **Cách khắc phục:**
  1. Kiểm tra lại cấu hình biến `SONAR_TOKEN` trong *GitLab > Settings > CI/CD > Variables*.
  2. Vào SonarQube Server kiểm tra quyền cấp phát (Permissions) cho token hoặc nhóm người dùng tương ứng.

---

### Q3: Job quét Java/Kotlin bị lỗi `java.lang.OutOfMemoryError: Java heap space`?
* **Nguyên nhân:** Dự án có codebase quá lớn vượt quá mức RAM cấp phát mặc định cho Java JVM của scanner.
* **Cách khắc phục:** Bổ sung biến môi trường tăng dung lượng Heap trong job:
  ```yaml
  variables:
    SONAR_SCANNER_OPTS: "-Xmx2048m"
  ```

---

### Q4: Tại sao SonarQube không hiển thị chỉ số Code Coverage (Coverage = 0%)?
* **Nguyên nhân:** SonarScanner không tự tạo coverage report mà chỉ đọc file report có sẵn. Nếu bước chạy test trước đó chưa chạy hoặc sai đường dẫn tới file report, coverage sẽ bằng 0%.
* **Cách khắc phục:** 
  - Đảm bảo đã chạy test trước khi chạy scanner (ví dụ: `npm run test:coverage` sinh ra `coverage/lcov.info`).
  - Khai báo chính xác đường dẫn report qua tham số (ví dụ: `sonar.javascript.lcov.reportPaths=coverage/lcov.info`).

---

### Q5: Khi nào nên đặt `sonar.qualitygate.wait=true`?
* **Trả lời:** Khi đặt `true`, SonarScanner sẽ liên tục poll SonarQube Server cho đến khi Compute Engine xử lý xong báo cáo (thường mất 10 - 30 giây) và trả về exit code tương ứng:
  - Nếu Quality Gate **PASSED**: Exit code `0` (Job xanh).
  - Nếu Quality Gate **FAILED**: Exit code `1` (Job đỏ/cảnh báo).
* Điều này rất hữu ích khi bạn muốn dùng SonarQube làm cổng chặn tự động trên các nhánh phát hành quan trọng.
