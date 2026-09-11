# TÀI LIỆU QUY TRÌNH VÀ KIẾN TRÚC CI / DEVSECOPS PIPELINE

> **Lưu ý quan trọng về tính chuẩn xác:** Tài liệu này được biên soạn dựa trên việc phân tích trực tiếp các file cấu hình và tài nguyên thực tế trong thư mục `CI/` (`README.MD`, `build-template.yml`, `devsecops-template.yml`, các ảnh chụp cấu hình). Tài liệu phân định rõ ràng giữa **Hiện trạng thực tế đang cấu hình (As-Is)**, **Các rủi ro bảo mật tồn tại**, và **Đề xuất cải tiến tối ưu (To-Be)**.

---

## CHƯƠNG I: TỔNG QUAN HỆ THỐNG VÀ KIẾN TRÚC TEMPLATE

### 1.1. Mục tiêu và Mô hình phân phối
Hệ thống **CI (Continuous Integration) & DevSecOps** tại FTECH được thiết kế theo mô hình **CI Pipeline tập trung (Centralized Templates)**:
* Toàn bộ các định nghĩa job chung được lưu trữ tại repository `gitlab-ci/ci-pipeline` (`https://gitlab.ftech.ai/gitlab-ci/ci-pipeline` hoặc `https://gg.ftech.ai/gitlab-ci/ci-pipeline`).
* Các dự án triển khai sẽ nhúng (include) file template thông qua tính năng `include:` của GitLab CI.
* Mục tiêu của CI là tự động hóa các bước kiểm thử, quét bảo mật, đóng gói container và phát hành image lên Harbor Registry (`registry.ftech.ai`), sau đó bàn giao cho hệ thống GitOps (ArgoCD) triển khai vào cụm Kubernetes.

### 1.2. Cấu trúc thư mục `CI/`
```text
CI/
├── README.MD                   # Hướng dẫn cấu hình, khai báo biến và nhúng template vào dự án
├── build-template.yml          # Template build Docker DinD cho môi trường dev, staging, prod
├── devsecops-template.yml      # Template quét bảo mật (detect-secrets, trivy, upload-bom, sonarqube, analyser)
└── images/                     # Ảnh chụp màn hình cấu hình thực tế trên GitLab UI
    ├── folder.png
    ├── gitlab-ci.png
    ├── variables.png           # Ảnh chụp các biến CI/CD và trạng thái cờ Protected/Masked
    ├── sonar-project-key.png
    ├── sonar-token.png
    └── ref-internal-repo.png
```

---

## CHƯƠNG II: SƠ ĐỒ VÀ LUỒNG HOẠT ĐỘNG THỰC TẾ (HIỆN TRẠNG AS-IS)

### 2.1. Thứ tự Stages thực tế theo `README.MD` gốc

Trong file [README.MD](file:///d:/FTECH/CI-CD/CI/README.MD) (mục `stages:`), thứ tự `stages` được khai báo nguyên bản như sau:

```yaml
stages:
  - build
  - detect-secrets
  - dependency-check
  - upload-bom
  - sonarqube-check
```

> ⚠️ **CẢNH BÁO THIẾT KẾ (RỦI RO BẢO MẬT THỰC TẾ):**
> Trong cấu hình hiện tại, stage **`build` đứng đầu tiên**. Điều này có nghĩa là khi lập trình viên push code, Docker Image sẽ được đóng gói và đẩy (`docker push`) lên Harbor Registry **trước khi** các stage kiểm tra bảo mật (`detect-secrets`, `dependency-check`, `sonarqube-check`) kịp chạy. Nếu code bị lộ token mật và `detect-secrets` chặn pipeline ở stage 2, thì **Container Image chứa mã nguồn lỗi/lộ secret đã tồn tại trên Registry rồi**.

### 2.2. Sơ đồ luồng hoạt động hiện tại (Hiện trạng thực tế - As-Is)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                1. KÍCH HOẠT PIPELINE (TRIGGER)                                   │
│                        Lập trình viên Push Code / Tạo Merge Request trên GitLab                  │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             STAGE 1: BUILD (CHẠY ĐẦU TIÊN THEO HIỆN TRẠNG)                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  • Nhánh dev / develop            ──► Job: build-dev     (Tự động chạy)                          │
│  • Nhánh staging                  ──► Job: build-staging (Tự động chạy)                          │
│  • Nhánh main / master / prod / tags ──► Job: build-prod (Yêu cầu kích hoạt thủ công: manual)    │
│                                                                                                  │
│  [QUY TRÌNH THỰC THI]:                                                                           │
│  1. In thông tin môi trường & in biến (bao gồm cả password ra log)                               │
│  2. docker login -u "$REGISTRY_PUSH_USER" -p "$REGISTRY_PUSH_PASSWORD" "registry.ftech.ai"       │
│  3. Tính toán APP_VERSION = [ENV]-[YYYY-MM-DD_HH-mm-ss]-[GIT_SHA_HOẶC_TAG]                       │
│  4. docker build & docker push lên Harbor Registry (registry.ftech.ai)                           │
│                                                                                                  │
│  ⚠️ Image đã được đẩy lên kho ngay tại đây!                                                     │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             CÁC STAGES DEVSECOPS & QUALITY GATES TIẾP THEO                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│  [STAGE 2: detect-secrets] (allow_failure: false)                                                │
│  • Quét lộ lọt Secret trong mã nguồn.                                                            │
│  • ⛔ NẾU PHÁT HIỆN SECRET: Pipeline bị STOP tại đây (Tuy nhiên Image đã bị push ở Stage 1).     │
│  • NẾU KHÔNG CÓ LỖI: Đi tiếp sang Stage 3.                                                      │
│                                                                                                  │
│  [STAGE 3: dependency-check] (allow_failure: true)                                               │
│  • Trivy quét lỗ hổng thư viện phụ thuộc (HIGH, CRITICAL) -> Xuất file SBOM result.json          │
│                                                                                                  │
│  [STAGE 4: upload-bom] (allow_failure: true)                                                     │
│  • Gửi HTTP POST đẩy file SBOM sang hệ thống OWASP Dependency-Track                              │
│                                                                                                  │
│  [STAGE 5: sonarqube-check] (allow_failure: true)                                                │
│  • Sonar Scanner phân tích Bugs, Code Smells, Security Hotspots lên SonarQube Server             │
│                                                                                                  │
│  [Job: gitlabci-analyser] (allow_failure: true)                                                  │
│  • Chạy script phân tích thời gian hàng đợi và thời lượng thực thi                               │
│                                                                                                  │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                BÀN GIAO GITOPS ENGINE (ARGOCD TRONG K8S)                         │
│  ArgoCD Image Updater bắt Tag mới trên Harbor -> Cập nhật Git Manifest -> Kéo Pod mới lên K8s   │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## CHƯƠNG III: PHÂN TÍCH CHI TIẾT TỪNG STAGE VÀ FILE TEMPLATE

### 3.1. Phân tích `devsecops-template.yml`

Tệp cấu hình gồm 5 jobs kiểm tra:

#### 1. Stage: `detect-secrets`
* **Image:** `registry.ftech.ai/public/is-chart/detect-secrets:v2.8`
* **Mã lệnh thực thi:**
  ```bash
  rm -rf .git/
  python /app/detect-secrets.py
  ```
* **Chi tiết kỹ thuật & Giả định:**
  * `rm -rf .git/`: Xóa thư mục git cục bộ để tránh việc công cụ quét lịch sử các commit cũ.
  * `python /app/detect-secrets.py`: Chạy script phân tích mã nguồn đóng gói sẵn bên trong container.
  * *(Dự kiến theo cơ chế chuẩn của các tool detect-secrets)*: Script sử dụng biểu thức chính quy (Regex) và tính toán Shannon Entropy để nhận diện các chuỗi có độ ngẫu nhiên cao nghi là Private Key, API Token, Password hard-code.
  * Hỗ trợ cấu hình bỏ qua qua biến môi trường của dự án:
    * `EXCLUDE_SECRETS`: Chuỗi bí mật mẫu / dummy data bỏ qua (phân tách bằng dấu `|`).
    * `EXCLUDE_FOLDERS`: Thư mục loại trừ không quét (phân tách bằng dấu `;`).
* **Quy tắc chặn:** `allow_failure: false` (Bắt buộc pass).

#### 2. Stage: `dependency-check` (SCA Scan)
* **Image:** `aquasec/trivy:0.56.1`
* **Mã lệnh thực thi:**
  ```bash
  before_script:
    - trivy image --quiet --download-db-only --debug
  script:
    - trivy filesystem --format cyclonedx --output ./result.json --quiet --exit-code 0 --no-progress --cache-dir /root/.cache/trivy --scanners vuln --ignore-unfixed -s HIGH,CRITICAL .
    - cat ./result.json > $RESULT
  artifacts:
    paths:
      - $RESULT
  ```
* **Giải thích tham số:**
  * `trivy filesystem`: Quét thư mục mã nguồn tìm CVE trong dependency.
  * `--format cyclonedx`: Xuất định dạng chuẩn Software Bill of Materials (SBOM) CycloneDX.
  * `--ignore-unfixed -s HIGH,CRITICAL`: Chỉ lọc các lỗ hổng mức độ High và Critical đã có bản vá.
  * `artifacts`: Lưu file `$RESULT` (`./result1.json`) cho stage tiếp theo.
* **Quy tắc:** `allow_failure: true`.

#### 3. Stage: `upload-bom`
* **Image:** `curlimages/curl`
* **Mã lệnh thực thi:**
  ```bash
  cat result1.json
  curl -X "POST" "https://dependency-track.dev.ftech.ai/api/v1/bom" \
       -H "Content-Type:multipart/form-data" \
       -H "X-Api-Key:$DEPENDENCY_TRACK_KEY" \
       -F "autoCreate=true" \
       -F "projectName=$CI_PROJECT_NAME" \
       -F "description=abcd" \
       -F "bom=@result1.json"
  ```
* **Ý nghĩa:** Đẩy tệp SBOM lên hệ thống OWASP Dependency-Track qua REST API để quản lý rủi ro thư viện tập trung.
* **Quy tắc:** `allow_failure: true`.

#### 4. Stage: `sonarqube-check`
* **Image:** `sonarsource/sonar-scanner-cli:latest`
* **Cấu hình & Mã lệnh:**
  ```yaml
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
  ```
* **Ý nghĩa:** Đẩy source code lên SonarQube Server phân tích chất lượng (Bugs, Code Smells, Security Hotspots). Tận dụng Cache để tăng tốc.
* **Quy tắc:** `allow_failure: true`.

#### 5. Stage: `gitlabci-analyser`
* **Image:** `registry.ftech.ai/public/is-chart/gitlabci-analyser:v0.2.0`
* **Mã lệnh:**
  ```bash
  python /tools/job-analyser.py --max_queue 30 --max_duration 300
  ```
* **Chi tiết & Giả định:**
  * Chạy script nội bộ để theo dõi thời gian chạy của Job.
  * *(Giả định)*: Tham số `--max_queue 30` và `--max_duration 300` là các ngưỡng giới hạn (nhiều khả năng tính theo đơn vị giây) nhằm cảnh báo tình trạng nghẽn Runner hoặc Job chạy quá lâu.
* **Quy tắc:** `allow_failure: true`.

---

### 3.2. Phân tích `build-template.yml` (Trích dẫn nguyên bản 100%)

#### 1. Đoạn mã Anchor `.build_template: &build` nguyên bản:

```yaml
.build_template: &build
  image: docker:$DOCKER_VERSION
  before_script:
    - docker info
    - docker images
    - echo $REGISTRY_PUSH_USER
    - echo $REGISTRY_PUSH_PASSWORD
    - echo $CI_REGISTRY
    - docker login -u "$REGISTRY_PUSH_USER" -p "$REGISTRY_PUSH_PASSWORD" "$CI_REGISTRY"
  script:
    - export APP_VERSION=$ENV_NAME-$(date +'%Y-%m-%d_%H-%M-%S')-`[ -n "$CI_COMMIT_TAG" ] && echo $CI_COMMIT_TAG || echo $CI_COMMIT_SHORT_SHA` && echo $APP_VERSION
    - docker build -t "$CI_REGISTRY_IMAGE:$APP_VERSION" -t "$CI_REGISTRY_IMAGE"  $BUILD_FOLDER -f $DOCKERFILE
    - docker push "$CI_REGISTRY_IMAGE:$APP_VERSION"
  services:
    - name: docker:$DOCKER_DIND_VERSION
      alias: docker
  allow_failure: false
  tags: [build]
```

> 🚨 **LỖ HỔNG BẢO MẬT NGHIÊM TRỌNG TỒN TẠI TRONG TEMPLATE HIỆN HÀNH:**
> Trong khối `before_script` trên có dòng lệnh:
> ```bash
> - echo $REGISTRY_PUSH_PASSWORD
> ```
> Lệnh này sẽ **in trực tiếp mật khẩu / token tài khoản Push Registry ra GitLab Job Console Log**. Bất kỳ ai có quyền xem Pipeline (kể cả quyền Developer/Reporter tùy cấu hình) đều có thể đọc được thông tin xác thực này trong plain text.

#### 2. Logic định danh phiên bản (`APP_VERSION`)
```bash
export APP_VERSION=$ENV_NAME-$(date +'%Y-%m-%d_%H-%M-%S')-`[ -n "$CI_COMMIT_TAG" ] && echo $CI_COMMIT_TAG || echo $CI_COMMIT_SHORT_SHA`
```
* **Mục đích:** Tạo tag duy nhất, có thứ tự thời gian để **ArgoCD Image Updater** nhận diện và tự động cập nhật Git Manifest.
* **Ví dụ:** `dev-2026-09-11_08-45-00-a1b2c3d`.

#### 3. Các job kế thừa theo môi trường:
* **`build-dev`**: Chạy tự động trên nhánh `dev`, `develop`.
* **`build-staging`**: Chạy tự động trên nhánh `staging`.
* **`build-prod`**: Chỉ kích hoạt trên `main`, `master`, `prod`, `tags` và có cờ `when: manual` (yêu cầu bấm chạy thủ công).

---

## CHƯƠNG IV: ĐỐI CHIẾU CẤU HÌNH BIẾN MÔI TRƯỜNG THỰC TẾ TRÊN GITLAB UI

### 4.1. Bảng đối chiếu cờ Protected / Masked theo ảnh chụp thực tế (`variables.png`)

Dựa trên ảnh chụp màn hình [variables.png](file:///d:/FTECH/CI-CD/CI/images/variables.png) và [README.MD](file:///d:/FTECH/CI-CD/CI/README.MD):

| Tên biến (Variable Key) | Protected (Bảo vệ) | Masked (Ẩn giá trị log) | Nguồn thông tin / Ghi chú |
| :--- | :---: | :---: | :--- |
| `DEPENDENCY_TRACK_KEY` | **✓ (Có)** | **✗ (Không)** | Xác nhận từ ảnh chụp thực tế `variables.png` |
| `SONAR_PROJECT_KEY` | **✓ (Có)** | **✗ (Không)** | Xác nhận từ ảnh chụp thực tế `variables.png` |
| `SONAR_TOKEN` | **✓ (Có)** | **✗ (Không)** | Xác nhận từ ảnh chụp thực tế `variables.png` |
| `REGISTRY_PUSH_USER` | *Chưa có trong ảnh* | *Chưa có trong ảnh* | Suy đoán dựa trên code `build-template.yml` |
| `REGISTRY_PUSH_PASSWORD` | *Chưa có trong ảnh* | *Chưa có trong ảnh* | Suy đoán dựa trên code `build-template.yml` |
| `SONAR_QUALITYGATE_WAIT` | *Chưa có trong ảnh* | *Chưa có trong ảnh* | Cấu hình tùy chọn theo lệnh Sonar Scanner |

> ⚠️ **CẢNH BÁO BẢO MẬT VỀ TRẠNG THÁI BIẾN:**
> Hai token nhạy cảm quan trọng là **`SONAR_TOKEN`** và **`DEPENDENCY_TRACK_KEY`** trong thực tế hiện **CHƯA ĐƯỢC BẬT CỜ MASKED** (`Masked = ✗`). Nếu trong bất kỳ script nào có lệnh echo hoặc in biến ra màn hình, token sẽ bị lộ nguyên văn trong log.

---

## CHƯƠNG V: MA TRẬN RỦI RO BẢO MẬT & ĐỀ XUẤT CẢI TIẾN

### 5.1. Bảng tổng hợp các rủi ro bảo mật trong cấu hình hiện tại (As-Is)

| STT | Vấn đề / Lỗ hổng phát hiện | Vị trí phát hiện | Mức độ rủi ro | Hậu quả thực tế |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Thứ tự Stage đặt `build` đầu tiên** | [README.MD](file:///d:/FTECH/CI-CD/CI/README.MD) (mục `stages:`) | 🔴 **HIGH** | Container Image bị build và push lên Harbor trước khi quét Secret/CVE. Nếu stage sau fail thì image bẩn vẫn nằm trên registry. |
| **2** | **Lệnh `echo $REGISTRY_PUSH_PASSWORD`** | [build-template.yml](file:///d:/FTECH/CI-CD/CI/build-template.yml) (mục `before_script:`) | 🔴 **CRITICAL** | In trực tiếp mật khẩu tài khoản Push Registry ra GitLab Console Log. |
| **3** | **Biến Token chưa được Masked** | [variables.png](file:///d:/FTECH/CI-CD/CI/images/variables.png) | 🟡 **MEDIUM** | `SONAR_TOKEN` và `DEPENDENCY_TRACK_KEY` không có cờ Masked, có nguy cơ lộ lọt khi debug pipeline. |

---

### 5.2. Đề xuất cải tiến chuẩn hóa (To-Be - Khuyến nghị thực hiện)

#### Đề xuất 1: Đảo thứ tự Stage chuẩn Shift-Left
Chuyển stage `build` xuống cuối cùng trong `.gitlab-ci.yml` của các dự án:

```yaml
# CẤU HÌNH ĐỀ XUẤT (SHIFT-LEFT CHUẨN):
stages:
  - detect-secrets      # 1. Quét lộ lọt Secret -> Chặn ngay nếu vi phạm
  - dependency-check    # 2. Quét CVE thư viện
  - upload-bom          # 3. Đẩy SBOM lên Dependency-Track
  - sonarqube-check     # 4. Phân tích chất lượng mã nguồn
  - gitlabci-analyser   # 5. Phân tích hiệu năng Runner
  - build               # 6. Chỉ Build & Push khi TẤT CẢ bước trên đã an toàn
```

#### Đề xuất 2: Xóa bỏ lệnh echo password trong `build-template.yml`
Sửa `before_script` của `build-template.yml` loại bỏ các dòng in nhạy cảm:

```yaml
# SỬA TRONG build-template.yml:
before_script:
  - docker info
  - docker images
  - docker login -u "$REGISTRY_PUSH_USER" -p "$REGISTRY_PUSH_PASSWORD" "$CI_REGISTRY"
```

#### Đề xuất 3: Bật cờ `Masked` trên GitLab Variables
Vào **Settings > CI/CD > Variables**, tích chọn **Mask variable** cho:
* `SONAR_TOKEN`
* `DEPENDENCY_TRACK_KEY`
* `REGISTRY_PUSH_PASSWORD`

---

## CHƯƠNG VI: BẢNG THAM CHIẾU CÔNG NGHỆ VÀ PHIÊN BẢN

| Hạng mục | Tên công nghệ / Dịch vụ | Phiên bản / Địa chỉ URL | Ghi chú & Vai trò |
| :--- | :--- | :--- | :--- |
| **CI Engine** | GitLab CI/CD | GitLab Self-hosted (`gitlab.ftech.ai`) | Điều phối và thực thi toàn bộ pipeline |
| **Container Engine** | Docker Engine & DinD | `docker:20.10.16` / `20.10.16-dind` | Xây dựng và đóng gói Container Image |
| **Container Registry** | Harbor Private Registry | `https://registry.ftech.ai` | Lưu trữ Docker Image bất biến |
| **Secret Scanning** | Python Detect-Secrets Engine | `detect-secrets:v2.8` | Quét chống lộ lọt thông tin mật |
| **SCA / CVE Scanner** | Aqua Security Trivy | `aquasec/trivy:0.56.1` | Quét lỗ hổng dependency & xuất CycloneDX |
| **SBOM Platform** | OWASP Dependency-Track | `https://dependency-track.dev.ftech.ai` | Quản trị rủi ro thành phần phần mềm |
| **SAST & Quality** | SonarQube Server & Scanner | `https://sonarqube.dev.ftech.ai` | Phân tích chất lượng mã nguồn & Quality Gate |
| **Runner Optimizer** | GitLab CI Analyser | `gitlabci-analyser:v0.2.0` | Đo lường hiệu năng thực thi job |
| **GitOps CD Handover**| ArgoCD Image Updater | Kubernetes Cluster Controller | Tự động phát hiện tag -> Sync Manifest |
