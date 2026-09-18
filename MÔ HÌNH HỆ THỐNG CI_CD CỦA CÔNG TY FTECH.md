# BÁO CÁO: LUỒNG THỰC THI CI/CD TỪ DEVELOPER PUSH CODE ĐẾN HOÀN TẤT CÁC STAGE DETECT-SECRETS, BUILD, DEPENDENCY-CHECK VÀ UPLOAD-BOM

```yaml
# File cấu hình .gitlab-ci.yml tại repository của dự án
include:
  - project: 'gitlab-ci/ci-pipeline'
    file:
      - 'build-common/build-template.yml'
      - 'devsecops/devsecops-template.yml'

variables:
  PROJECT: "project-name"
  CI_REGISTRY: "registry.ftech.ai"
  CI_REGISTRY_IMAGE: "registry.ftech.ai/ftech/project-name"
  DOCKER_VERSION: "20.10.16"
  DOCKER_DIND_VERSION: "20.10.16-dind"
  RESULT: "./result1.json"

stages:
  - detect-secrets
  - build
  - dependency-check
  - upload-bom
  - sonarqube-check
  # gitlabci-analyser: tuỳ chọn, project tự thêm nếu muốn dùng, không có sẵn trong README mẫu
```

## 1. TỔNG QUAN LUỒNG THỰC THI (WORKFLOW OVERVIEW)

Hệ thống CI/CD của FTECH được xây dựng trên nền tảng **GitLab CI/CD**, sử dụng mô hình **Centralized CI Templates** lưu tại repository `gitlab-ci/ci-pipeline`. Quy trình xử lý từ khi Developer đẩy mã nguồn đến khi hoàn tất 4 stage cốt lõi (`detect-secrets` ➔ `build` ➔ `dependency-check` ➔ `upload-bom`) tuân thủ chiến lược **Shift-Left Security** (kiểm soát bảo mật ngay từ đầu) được mô tả tổng quan qua sơ đồ sau:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        1. GIAI ĐOẠN KHỞI TẠO PIPELINE (GITLAB SERVER)                                   │
│                                                                                                         │
│  [Developer] ──── git push ────► [GitLab Server] ────► [Merge Template gitlab-ci/ci-pipeline]           │
│                                                              │                                          │
│                                                              ▼                                          │
│                    [Xác định thứ tự Stage: detect-secrets ──► build ──► dependency-check ──► upload-bom]│
└──────────────────────────────────────────────────────────────┬──────────────────────────────────────────┘
                                                               │
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        2. STAGE: detect-secrets (Chạy đầu tiên - Tag: devsecops)                        │
│                                                                                                         │
│  GitLab Runner tag: devsecops nhận job                                                                  │
│  │                                                                                                      │
│  ▼ (Single Container - registry.ftech.ai/public/is-chart/detect-secrets:v2.8)                           │
│  • rm -rf .git/                   (Xoá lịch sử Git, chỉ quét mã nguồn commit hiện tại)                  │
│  • python /app/detect-secrets.py  (Quét secret/token/key; lọc theo EXCLUDE_SECRETS / EXCLUDE_FOLDERS)    │
│  │                                                                                                      │
│  [allow_failure: false] ──┬─❌ PHÁT HIỆN SECRET CHƯA WHITELIST ────► [DỪNG PIPELINE ➔ Báo lỗi Dev]      │
│                           └─✅ MÃ NGUỒN SẠCH (PASS) ───────────────► [Chuyển tiếp sang Stage 2: build]  │
└──────────────────────────────────────────────────────────────┬──────────────────────────────────────────┘
                                                               │
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        3. STAGE: build (Chạy khi mã sạch secret - Tag: build)                           │
│                                                                                                         │
│  Kiểm tra nhánh (only:) ──┬── dev / develop ────────► Job: build-dev     (Tự động)                      │
│                           ├── staging ──────────────► Job: build-staging (Tự động)                      │
│                           └── main/master/prod/tags ─► Job: build-prod    (when: manual ➔ Bấm Play)     │
│                                                             │                                           │
│                                                             ▼ (Runner tag: build - Docker-in-Docker)    │
│                           • docker login vào registry.ftech.ai                                          │
│                           • docker build & push "$CI_REGISTRY_IMAGE:$APP_VERSION"                       │
│                                                             │                                           │
│  [allow_failure: false] ──┬─❌ BUILD THẤT BẠI ─────────────────────► [DỪNG PIPELINE ➔ Báo lỗi Dev]      │
│                           └─✅ BUILD & PUSH THÀNH CÔNG (PASS) ─────► [Chuyển tiếp sang Stage 3]         │
└──────────────────────────────────────────────────────────────┬──────────────────────────────────────────┘
                                                               │
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        4. STAGE: dependency-check (Quét lỗ hổng SCA & Tạo SBOM - Tag: devsecops)        │
│                                                                                                         │
│  GitLab Runner tag: devsecops nhận job                                                                  │
│  │                                                                                                      │
│  ▼ (Single Container - aquasec/trivy:0.56.1)                                                            │
│  • before_script: trivy image --quiet --download-db-only --debug  (Tải CSDL lỗ hổng CVE)                 │
│  • script: trivy filesystem --format cyclonedx --output ./result.json -s HIGH,CRITICAL .                │
│            cat ./result.json > $RESULT ($RESULT = "./result1.json")                                     │
│  • artifacts: Lưu trữ ./result1.json để chuyển tiếp sang stage upload-bom                               │
│  │                                                                                                      │
│  [allow_failure: true] ────────────────────────────────────────────► [Chuyển tiếp sang Stage 4]         │
└──────────────────────────────────────────────────────────────┬──────────────────────────────────────────┘
                                                               │
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        5. STAGE: upload-bom (Đẩy SBOM lên OWASP Dependency-Track - Tag: devsecops)      │
│                                                                                                         │
│  GitLab Runner tag: devsecops nhận job                                                                  │
│  │                                                                                                      │
│  ▼ (Single Container - curlimages/curl)                                                                 │
│  • Nhận artifact result1.json từ stage dependency-check                                                 │
│  • curl -X POST "https://dependency-track.dev.ftech.ai/api/v1/bom"                                       │
│         -H "X-Api-Key:$DEPENDENCY_TRACK_KEY" -F "autoCreate=true" -F "bom=@result1.json"               │
│  │                                                                                                      │
│  [allow_failure: true] ────────────────────────────────────────────► [Chuyển tiếp sang Stage 5: Sonar]  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PHẦN CHUNG: GIAI ĐOẠN KHỞI TẠO PIPELINE (GITLAB SERVER)

*Giai đoạn này diễn ra tập trung tại GitLab Server trước khi điều phối công việc xuống các máy chủ thực thi (GitLab Runners).*

### 1. Sự kiện kích hoạt Pipeline (Pipeline Trigger)
- **Hành động:** Developer thực hiện lệnh `git push` mã nguồn từ máy local lên bất kỳ nhánh (`branch`) hoặc gắn nhãn (`tag`) nào trên GitLab Server.
- **Phản ứng của GitLab:** GitLab Server bắt được sự kiện Git Push Event và tự động khởi tạo (trigger) một Pipeline CI/CD mới cho commit tương ứng mà không yêu cầu thao tác bấm nút thủ công.

### 2. Đọc và hợp nhất cấu hình (Config Parsing & Include Merging)
- **Đọc file cấu hình gốc:** GitLab CI Parser đọc file `.gitlab-ci.yml` tại thư mục gốc của repository dự án.
- **Kéo template tập trung (`include`):** Khi gặp chỉ thị `include`, GitLab sẽ phân giải và tải các file template từ repository trung tâm `gitlab-ci/ci-pipeline`:
  - `build-common/build-template.yml`
  - `devsecops/devsecops-template.yml`
- **Hợp nhất (Merge Engine):** 
  - GitLab thực hiện hợp nhất toàn bộ khai báo biến (`variables`), cấu hình job ẩn định nghĩa khuôn mẫu (`.build_template: &build`), các merge key (`<<: *build`), và các job cụ thể vào một cây cấu hình pipeline thống nhất.
  - Các biến toàn cục (`BUILD_FOLDER`, `DOCKERFILE`, `CI_REGISTRY`, `DOCKER_VERSION`, `RESULT`...) được nạp sẵn vào cấu hình thực thi.

### 3. Xác định thứ tự Stage (Stage Execution Graph)
- Dựa trên khai báo `stages:` trong `.gitlab-ci.yml`:
  ```yaml
  stages:
    - detect-secrets
    - build
    - dependency-check
    - upload-bom
    - sonarqube-check
    # gitlabci-analyser: tuỳ chọn, project tự thêm nếu muốn dùng, không có sẵn trong README mẫu
  ```
- **Quy tắc thực thi tuần tự chuẩn DevSecOps:**
  1. `detect-secrets` đứng vị trí đầu tiên để ngăn chặn việc đưa mã nguồn chứa thông tin nhạy cảm vào container image.
  2. `build` đứng vị trí thứ hai, chỉ chạy khi mã nguồn đã được xác nhận sạch secret.
  3. `dependency-check` đứng vị trí thứ ba để phân tích thành phần phần mềm (SCA) và tạo file Software Bill of Materials (SBOM).
  4. `upload-bom` đứng vị trí thứ tư, tiêu thụ artifact SBOM sinh ra từ stage 3 để tải lên nền tảng quản lý tập trung OWASP Dependency-Track.
- **Ràng buộc phụ thuộc:** Stage đứng trước phải hoàn thành (hoặc thỏa mãn `allow_failure`) thì GitLab Server mới lên lịch (`schedule`) cho stage kế tiếp.

---

## 3. PHẦN A: STAGE `detect-secrets` (QUÉT SECRET VÀ MÃ NHẠY CẢM)

*Stage này chạy đầu tiên ngay khi Developer đẩy mã nguồn, đảm bảo nguyên tắc Shift-Left Security: không để lọt API Key, Private Key, Token, Password vào quy trình đóng gói image.*

### A1–A2. Runner nhận Job và Chuẩn bị Executor
- Khi pipeline khởi tạo, GitLab Server đưa job `detect-secrets` vào trạng thái `pending`.
- Máy chủ **GitLab Runner** được gắn tag `[devsecops]` tiếp nhận job.
- **Mô hình Single Container:** Job chỉ khai báo `image:` mà **không** có `services:`, do đó Docker Executor chỉ cần tạo duy nhất **1 container đơn lẻ**, không cần Docker daemon và không tiêu tốn tài nguyên DinD.

### A3–A4. Tải Image và Khởi tạo Container
- Runner kéo image công cụ quét bảo mật chuyên dụng nội bộ:
  ```text
  registry.ftech.ai/public/is-chart/detect-secrets:v2.8
  ```
- Khởi tạo 1 container độc lập từ image này để chuẩn bị thực thi phân tích mã nguồn.

### A5. Clone / Checkout mã nguồn (Fetch Workspace)
- Container phụ (`gitlab-runner-helper`) thực hiện clone mã nguồn dự án từ GitLab Server về thư mục workspace của job, checkout chính xác tại commit SHA vừa push.

### A6. Tiêm nạp biến môi trường và cấu hình loại trừ (Exclusions)
- Nạp các biến hệ thống mặc định của GitLab.
- Nạp các biến cấu hình loại trừ do dự án định nghĩa trong `.gitlab-ci.yml` (nếu có):
  - `EXCLUDE_SECRETS`: Chuỗi các secret giả lập hoặc chuỗi đã được duyệt ngoại lệ, ngăn cách bằng dấu `|` (ví dụ: `"token_test_123|dummy_password_abc"`).
  - `EXCLUDE_FOLDERS`: Danh sách các thư mục không quét, ngăn cách bằng dấu `;` (ví dụ: `"static;store/static;vendor;node_modules"`).

### A7. Thực thi tập lệnh phân tích bảo mật (Security Scan Script)
Container thực thi tập lệnh:

```sh
# 1. Xóa bỏ thư mục lịch sử Git
rm -rf .git/

# 2. Chạy công cụ phân tích quét secret
python /app/detect-secrets.py
```

- **Mục đích của `rm -rf .git/`:** Loại bỏ toàn bộ metadata và lịch sử commit cũ, chỉ giữ lại mã nguồn tại thời điểm hiện tại của commit. Việc này giúp tăng tốc độ quét và tránh báo động giả (false positive) từ các chuỗi secret cũ đã từng được xoá trong lịch sử.
- **Công cụ `detect-secrets.py`:** Quét toàn bộ file trong thư mục để tìm chuỗi nghi là secret/token/key theo thuật toán Regex và Entropy kết hợp đối chiếu whitelist từ `EXCLUDE_SECRETS`/`EXCLUDE_FOLDERS`.

### A8. Thu thập Log và Đánh giá Exit Code
- Toàn bộ kết quả quét chi tiết (file, dòng code vi phạm, loại secret) được ghi vào log và stream về giao diện GitLab CI.
- **Nếu phát hiện Secret không nằm trong danh sách whitelist:** Script trả về `exit code != 0` ➔ Job nhận trạng thái **Failed**.
- **Nếu mã nguồn sạch (không có secret rò rỉ):** Script trả về `exit code = 0` ➔ Job nhận trạng thái **Passed**.

### A9. Tác động tới Pipeline (Security Gate)
- Job `detect-secrets` có cấu hình nghiêm ngặt: `allow_failure: false`.
- **Nếu phát hiện Secret:** Pipeline dừng ngay lập tức. Toàn bộ các stage phía sau như `build`, `dependency-check`, `upload-bom`, và `sonarqube-check` **bị chặn đứng hoàn toàn**, ngăn ngừa triệt để nguy cơ đóng gói secret vào Docker Image.

---

## 4. PHẦN B: STAGE `build` (ĐÓNG GÓI VÀ ĐẨY DOCKER IMAGE)

*Stage này chạy sau khi Stage `detect-secrets` đã vượt qua an toàn, chịu trách nhiệm đóng gói mã nguồn ứng dụng thành Docker Image và đẩy lên FTECH Private Container Registry (`registry.ftech.ai`).*

### B1. Xác định Job được kích hoạt (Rule Matching)
- GitLab kiểm tra nhánh/tag vừa push đối chiếu với điều kiện `only:` của 3 job build được khai báo trong template:
  - `build-dev`: Kích hoạt khi push vào nhánh `dev`, `develop` (chạy tự động).
  - `build-staging`: Kích hoạt khi push vào nhánh `staging` (chạy tự động).
  - `build-prod`: Kích hoạt khi push vào nhánh `main`, `master`, `prod`, hoặc `tags`. Job này có cấu hình `when: manual` nên sau khi stage khởi tạo, job sẽ dừng ở trạng thái chờ và **cần người quản trị/lead bấm nút "Play" (Run)** trên giao diện GitLab để thực thi.
- **Đặc điểm:** Tại một thời điểm push lên một nhánh xác định, **chỉ duy nhất đúng 1 job build** thỏa mãn điều kiện và được chuyển sang trạng thái `pending`.

### B2. Runner nhận Job (Job Dispatching)
- Các máy chủ **GitLab Runner** được gắn tag `[build]` liên tục gửi yêu cầu kiểm tra (long-polling) đến GitLab Server.
- Khi phát hiện job ở trạng thái `pending` khớp đúng tag `build`, Runner sẽ tiếp nhận job, tải toàn bộ metadata cấu hình (tên image, services, script, biến môi trường...) về để xử lý.

### B3. Chuẩn bị Executor (Docker-in-Docker Executor)
- Vì job khai báo đồng thời `image: docker:$DOCKER_VERSION` và `services: - name: docker:$DOCKER_DIND_VERSION`, Runner bắt buộc phải sử dụng **Docker Executor** với quyền `privileged: true` trên cấu hình Runner.
- Docker Executor thiết lập mô hình multi-container trên cùng một mạng bridge ảo nội bộ của job.

### B4. Tải Image (Pulling Container Images)
Runner thực hiện kéo 2 image chính thức từ **Docker Hub**:
1. **Container chính (App/CLI Container):** `docker:20.10.16` — Chứa Docker CLI để chạy `before_script` và `script`.
2. **Container dịch vụ (Service/Daemon Container):** `docker:20.10.16-dind` — Chứa Docker Daemon thật (`dockerd`) chịu trách nhiệm biên dịch và quản lý các layer Docker image.

### B5. Khởi tạo Container và Mạng nội bộ
- Runner tạo mạng bridge riêng cho job.
- Khởi động service container với `alias: docker` lắng nghe các lệnh Docker engine từ mạng nội bộ.
- Khởi động container chính và trỏ kết nối Docker Client đến daemon qua alias `docker`.

### B6. Thực thi tập lệnh Build và Push

```sh
# 1. Giai đoạn before_script (Kiểm tra & Đăng nhập)
docker info                                              # Kiểm tra tình trạng Docker daemon
docker images                                            # Liệt kê các image cục bộ
echo $REGISTRY_PUSH_USER                                 # In thông tin user (khuyến nghị Masked trên GitLab)
echo $REGISTRY_PUSH_PASSWORD                             # In thông tin password (khuyến nghị Masked trên GitLab)
echo $CI_REGISTRY                                        # In registry URL (registry.ftech.ai)
docker login -u "$REGISTRY_PUSH_USER" -p "$REGISTRY_PUSH_PASSWORD" "$CI_REGISTRY" # Đăng nhập Private Registry

# 2. Giai đoạn script (Gắn tag, Build và Push Image)
# Tính toán APP_VERSION: kết hợp ENV_NAME + Timestamp + (Tag hoặc Commit Short SHA)
export APP_VERSION=$ENV_NAME-$(date +'%Y-%m-%d_%H-%M-%S')-`[ -n "$CI_COMMIT_TAG" ] && echo $CI_COMMIT_TAG || echo $CI_COMMIT_SHORT_SHA` && echo $APP_VERSION

# Đóng gói image với 2 tag (tag có phiên bản cụ thể và tag base)
docker build -t "$CI_REGISTRY_IMAGE:$APP_VERSION" -t "$CI_REGISTRY_IMAGE" $BUILD_FOLDER -f $DOCKERFILE

# Đẩy image kèm version lên Private Registry
docker push "$CI_REGISTRY_IMAGE:$APP_VERSION"
```

### B7. Tác động tới Pipeline (Build Gate)
- Job build được cấu hình `allow_failure: false`.
- **Nếu Job Build Failed:** Toàn bộ Pipeline lập tức chuyển sang trạng thái **Failed** và dừng lại. Stage `dependency-check` và các stage sau bị bỏ qua.
- **Nếu Job Build Passed:** Image an toàn đã nằm trên Harbor Registry sẵn sàng cho GitOps (ArgoCD), pipeline chuyển tiếp sang stage phân tích thành phần phần mềm `dependency-check`.

---

## 5. PHẦN C: STAGE `dependency-check` (QUÉT LỖ HỔNG SCA VÀ SINH BẢN KÊ SBOM VỚI TRIVY)

*Stage này chịu trách nhiệm phân tích thành phần phần mềm (Software Composition Analysis - SCA), kiểm tra toàn bộ thư viện phụ thuộc của dự án để phát hiện các lỗ hổng bảo mật (CVE) đã biết, đồng thời xuất bản kê khai phần mềm SBOM theo chuẩn quốc tế CycloneDX.*

### C1. Cấu hình Job trong `devsecops-template.yml`

```yaml
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

### C2. Runner nhận Job và Chuẩn bị Môi trường
- **Tag tiếp nhận:** Runner có tag `[devsecops]`.
- **Mô hình Container:** Single Container chạy trực tiếp image `aquasec/trivy:0.56.1` (Trivy là công cụ bảo mật nguồn mở chuẩn công nghiệp phát triển bởi Aqua Security).
- **Entrypoint Override (`entrypoint: [""]`):** Xóa entrypoint mặc định của image Trivy để GitLab Runner có thể gọi trực tiếp shell script (`sh`/`bash`) mà không bị xung đột.

### C3. Phân tích chi tiết quy trình thực thi tập lệnh

#### 1. Giai đoạn `before_script` (Cập nhật Cơ sở dữ liệu Lỗ hổng)
```sh
trivy image --quiet --download-db-only --debug
```
- **Mục đích:** Tải và cập nhật bản snapshot mới nhất của cơ sở dữ liệu lỗ hổng bảo mật (Vulnerability Database) từ GitHub/Aqua Security về cache của Runner trước khi tiến hành quét mã nguồn.
- `--download-db-only`: Chỉ tải CSDL CVE mà không thực hiện hành động quét image nào.
- `--quiet`: Tắt bớt các log tải dữ liệu thừa để log CI tinh gọn.
- `--debug`: Ghi log chi tiết tiến trình kết nối máy chủ database trong trường hợp gặp lỗi mạng.

#### 2. Giai đoạn `script` (Quét Lỗ hổng và Sinh SBOM)
```sh
trivy filesystem --format cyclonedx --output ./result.json --quiet --exit-code 0 --no-progress --cache-dir /root/.cache/trivy --scanners vuln --ignore-unfixed -s HIGH,CRITICAL .
cat ./result.json > $RESULT
```

*Ý nghĩa kỹ thuật của từng tham số lệnh:*
- `filesystem` (hoặc `fs`): Chỉ định đối tượng quét là thư mục mã nguồn hiện tại (`.`), quét sâu vào các tệp khai báo và lock dependency (`package-lock.json`, `pom.xml`, `requirements.txt`, `go.sum`, `composer.lock`, `Gemfile.lock`,...).
- `--format cyclonedx`: Định dạng đầu ra theo chuẩn **CycloneDX JSON** (chuẩn quốc tế của OWASP về Software Bill of Materials - SBOM), cho phép biểu diễn đầy đủ cấu trúc cây phụ thuộc của phần mềm.
- `--output ./result.json`: Ghi toàn bộ kết quả phân tích SBOM vào tệp tin `result.json`.
- `--exit-code 0`: Luôn trả về mã thoát thành công (0) để job không làm dừng pipeline đột ngột ở bước này; kết quả sẽ được đưa lên hệ thống giám sát tập trung để quản lý vòng đời lỗ hổng.
- `--no-progress`: Tắt thanh tiến trình hiển thị dạng tương tác để tránh làm tràn màn hình log CI.
- `--cache-dir /root/.cache/trivy`: Đường dẫn thư mục lưu trữ cache cơ sở dữ liệu CVE cục bộ.
- `--scanners vuln`: Chỉ định loại máy quét chuyên biệt là quét lỗ hổng thư viện (**Vulnerability Scanner**).
- `--ignore-unfixed`: **Cực kỳ quan trọng** — Bỏ qua các lỗ hổng chưa có bản vá phát hành từ phía nhà phát triển thư viện, giúp tránh báo động giả gây nhiễu cho đội ngũ phát triển.
- `-s HIGH,CRITICAL`: Thiết lập bộ lọc mức độ nghiêm trọng, chỉ tập trung xử lý các rủi ro ở mức **Cao (HIGH)** và **Cực kỳ nguy hiểm (CRITICAL)**.
- `cat ./result.json > $RESULT`: Đẩy nội dung file `result.json` vào tệp tin được định nghĩa trong biến toàn cục `$RESULT` (`./result1.json`).

### C4. Cơ chế chuyển giao Artifacts
- Cấu hình `artifacts: paths: - $RESULT` chỉ định cho GitLab Runner thu thập tệp tin `./result1.json` sau khi job kết thúc và tải lên lưu trữ tạm thời tại GitLab Server.
- File Artifact này là **đầu vào bắt buộc (Input)** cho stage tiếp theo (`upload-bom`).

### C5. Đánh giá chính sách `allow_failure: true`
- Job được gán cờ `allow_failure: true`.
- Nếu quá trình quét gặp sự cố ngoài ý muốn (mạng tải database bị gián đoạn, file manifest dị thường), GitLab CI sẽ hiển thị cảnh báo màu cam (warning) nhưng không làm gián đoạn toàn bộ pipeline của dự án.

---

## 6. PHẦN D: STAGE `upload-bom` (TỰ ĐỘNG ĐẨY SBOM LÊN OWASP DEPENDENCY-TRACK)

*Stage này chịu trách nhiệm tự động hóa việc đưa bản kê khai phần mềm (SBOM) vừa tạo từ Trivy lên nền tảng quản lý rủi ro chuỗi cung ứng phần mềm tập trung OWASP Dependency-Track của công ty.*

### D1. Cấu hình Job trong `devsecops-template.yml`

```yaml
upload-bom:
  stage: upload-bom
  image:
    name: curlimages/curl
    entrypoint: [""]
  script:
    - cat result1.json
    - curl -X "POST" "https://dependency-track.dev.ftech.ai/api/v1/bom" -H "Content-Type:multipart/form-data" -H "X-Api-Key:$DEPENDENCY_TRACK_KEY" -F "autoCreate=true" -F "projectName=$CI_PROJECT_NAME" -F "description=abcd" -F "bom=@result1.json"
  tags: [devsecops]
  allow_failure: true
```

### D2. Runner nhận Job và Tiếp nhận Artifacts
- **Tag tiếp nhận:** Runner có tag `[devsecops]`.
- **Image sử dụng:** `curlimages/curl` — Một container siêu nhẹ chỉ chứa công cụ mạng `curl` chính thức.
- **Kế thừa Artifact:** GitLab Runner tự động tải xuống tệp `result1.json` từ GitLab Server (đã được stage `dependency-check` lưu lại trước đó) và đặt vào thư mục làm việc của job.

### D3. Phân tích chi tiết quy trình thực thi tập lệnh

```sh
# 1. Đọc và kiểm tra tính hợp lệ của tệp SBOM
cat result1.json

# 2. Gửi yêu cầu HTTP POST Multipart tới API của OWASP Dependency-Track
curl -X "POST" "https://dependency-track.dev.ftech.ai/api/v1/bom" \
     -H "Content-Type:multipart/form-data" \
     -H "X-Api-Key:$DEPENDENCY_TRACK_KEY" \
     -F "autoCreate=true" \
     -F "projectName=$CI_PROJECT_NAME" \
     -F "description=abcd" \
     -F "bom=@result1.json"
```

*Ý nghĩa các tham số gọi API:*
- `POST https://dependency-track.dev.ftech.ai/api/v1/bom`: Điểm cuối (Endpoint) tiếp nhận tải lên SBOM của hệ thống Dependency-Track nội bộ FTECH.
- `-H "X-Api-Key:$DEPENDENCY_TRACK_KEY"`: Header xác thực quyền truy cập API. Biến `$DEPENDENCY_TRACK_KEY` được lưu trữ an toàn và bảo mật dưới dạng **Masked / Protected Variable** trong mục CI/CD Settings của GitLab.
- `-F "autoCreate=true"`: Cờ thông minh cho phép Dependency-Track tự động tạo mới một Project trên hệ thống nếu đây là lần đầu tiên repository này chạy pipeline, không đòi hỏi quản trị viên phải tạo project thủ công trước.
- `-F "projectName=$CI_PROJECT_NAME"`: Tự động gán tên dự án trên Dependency-Track theo đúng tên repository GitLab (`$CI_PROJECT_NAME`).
- `-F "description=abcd"`: Trường mô tả phụ đính kèm bản build.
- `-F "bom=@result1.json"`: Đính kèm tệp tin SBOM định dạng CycloneDX JSON từ đĩa vào payload gửi đi.

### D4. Vai trò của OWASP Dependency-Track trong hệ sinh thái FTECH
Sau khi SBOM được đẩy lên thành công:
1. **Quản lý rủi ro liên tục (Continuous Monitoring):** Ngay cả khi dự án không có commit mới, mỗi khi thế giới công bố một CVE mới, Dependency-Track sẽ tự động đối soát với kho SBOM để cảnh báo nguy cơ tức thì.
2. **Theo dõi Giấy phép (License Compliance):** Tự động phát hiện các thư viện vi phạm bản quyền phần mềm (GPL, AGPL...).
3. **Chấm điểm Rủi ro (Risk Scoring):** Cung cấp Dashboard trực quan cho ban lãnh đạo và kỹ sư bảo mật về chỉ số rủi ro của toàn bộ sản phẩm trong công ty.

---

## 7. PHẦN E: STAGE `sonarqube-check` (PHÂN TÍCH CHẤT LƯỢNG MÃ NGUỒN VỚI SONARQUBE)

*Stage này chịu trách nhiệm đẩy toàn bộ mã nguồn dự án lên nền tảng SonarQube Server nội bộ FTECH (`sonarqube.dev.ftech.ai`) để phân tích tĩnh (Static Analysis) toàn diện: phát hiện Bugs, Code Smells, Security Hotspots và đo lường Technical Debt.*

### E1. Cấu hình Job trong `devsecops-template.yml`

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

### E2. Runner nhận Job và Chuẩn bị Môi trường
- **Tag tiếp nhận:** Runner có tag `[devsecops]`.
- **Mô hình Container:** Single Container chạy image chính thức `sonarsource/sonar-scanner-cli:latest` từ Docker Hub — bộ công cụ phân tích tĩnh (static analyzer) của SonarSource.
- **Entrypoint Override (`entrypoint: [""]`):** Xóa entrypoint mặc định của image để GitLab Runner thực thi trực tiếp lệnh shell.

### E3. Phân tích chi tiết cấu hình và biến môi trường

#### Khối `variables`
| Biến | Giá trị | Ý nghĩa |
| :--- | :--- | :--- |
| `SONAR_USER_HOME` | `${CI_PROJECT_DIR}/.sonar` | Thư mục làm việc nội bộ của SonarQube Scanner trong workspace của job. |
| `GIT_DEPTH` | `"0"` | Yêu cầu GitLab clone **toàn bộ lịch sử Git** (unshallow clone). Cần thiết để SonarQube tính toán chính xác chỉ số blame, date, và phân tích sự thay đổi của code theo thời gian. |
| `SONAR_HOST_URL` | `https://sonarqube.dev.ftech.ai` | Địa chỉ SonarQube Server nội bộ FTECH mà scanner sẽ kết nối gửi kết quả phân tích. |

#### Khối `cache`
```yaml
cache:
  key: "${CI_JOB_NAME}"
  paths:
    - .sonar/cache
```
- **Cơ chế hoạt động:** GitLab Runner lưu trữ thư mục `.sonar/cache` (chứa dữ liệu index tĩnh, các rule đã tải về từ SonarQube Server) vào bộ nhớ đệm (cache) dùng chung giữa các lần chạy pipeline.
- **Lợi ích:** Tránh phải tải lại toàn bộ rule set và metadata từ server mỗi lần chạy, giảm đáng kể thời gian thực thi của job từ các lần chạy thứ 2 trở đi.

### E4. Phân tích chi tiết tập lệnh thực thi

```sh
sonar-scanner -Dsonar.projectKey=$SONAR_PROJECT_KEY -Dsonar.qualitygate.wait=$SONAR_QUALITYGATE_WAIT
```

*Ý nghĩa kỹ thuật của các tham số:*
- `-Dsonar.projectKey=$SONAR_PROJECT_KEY`: Khoá định danh duy nhất (Unique Key) của dự án trên SonarQube Server. Biến `$SONAR_PROJECT_KEY` được khai báo dưới dạng **Protected Variable** trong phần *Settings > CI/CD > Variables* của dự án trên GitLab, tránh lộ thông tin trong cấu hình file.
- `-Dsonar.qualitygate.wait=$SONAR_QUALITYGATE_WAIT`: Nếu biến này có giá trị `true`, scanner sẽ **đợi (blocking)** kết quả đánh giá từ SonarQube Quality Gate (cổng chất lượng) trước khi kết thúc job và trả về exit code tương ứng. Nếu `false` hoặc không khai báo, scanner chỉ tải kết quả lên mà không chờ đánh giá.

### E5. Cơ chế Quality Gate
SonarQube Quality Gate là bộ tiêu chí chất lượng tùy chỉnh được thiết lập bởi DevSecOps/Lead, ví dụ:
- Tỷ lệ Code Coverage tối thiểu (ví dụ: $\geq 80\%$).
- Số lượng Bugs mới = 0.
- Số lượng Security Hotspots chưa xem xét = 0.

**Nếu Quality Gate PASS:** Job kết thúc thành công, Pipeline chuyển tiếp stage tiếp theo.
**Nếu Quality Gate FAIL:** Do cấu hình `allow_failure: true`, job báo cảnh báo màu cam (Warning) nhưng **không làm gián đoạn Pipeline** — đảm bảo luồng phát hành không bị chặn bởi vấn đề chất lượng code trong ngắn hạn.

### E6. Tích hợp cấu hình dự án phía GitLab
Để stage `sonarqube-check` hoạt động chính xác, dự án cần khai báo 2 biến trong *Settings > CI/CD > Variables*:
1. **`SONAR_PROJECT_KEY`** — Khóa định danh của project trên SonarQube.
2. **`SONAR_QUALITYGATE_WAIT`** — Đặt `true` để chờ kết quả Quality Gate, hoặc `false` để chỉ đẩy kết quả lên.

---

## 8. PHẦN F: STAGE `gitlabci-analyser` (GIÁM SÁT HIỆU NĂNG VÀ ĐỘ TRỄ RUNNER - TUỲ CHỌN)

*Stage này đóng vai trò là công cụ quan sát (Observability & Profiling) cho hạ tầng CI/CD, theo dõi thời gian chờ hàng đợi và thời lượng thực thi của các Job nhằm phát hiện sớm tình trạng quá tải hoặc nghẽn tài nguyên Runner.*

### E1. Cấu hình Job trong `devsecops-template.yml`

```yaml
gitlabci-analyser:
  stage: gitlabci-analyser
  image:
    name: registry.ftech.ai/public/is-chart/gitlabci-analyser:v0.2.0
    entrypoint: [""]
  script:
    - python /tools/job-analyser.py --max_queue 30 --max_duration 300
  tags: [devsecops]
  allow_failure: true
```

### F2. Runner nhận Job và Chuẩn bị Môi trường
- **Tag tiếp nhận:** Runner có tag `[devsecops]`.
- **Mô hình Container:** Single Container chạy trực tiếp image nội bộ `registry.ftech.ai/public/is-chart/gitlabci-analyser:v0.2.0` (đóng gói sẵn runtime Python cùng các script telemetry phân tích CI/CD).
- **Entrypoint Override (`entrypoint: [""]`):** Xóa entrypoint mặc định của Docker image để GitLab Runner thực thi trực tiếp câu lệnh script.

### F3. Phân tích chi tiết cơ chế hoạt động của `job-analyser.py`

Container thực thi tập lệnh:
```sh
python /tools/job-analyser.py --max_queue 30 --max_duration 300
```

*Ý nghĩa kỹ thuật của các tham số phân tích:*
- `--max_queue 30` (Ngưỡng hàng đợi - 30 giây):
  - Đo lường khoảng thời gian từ lúc Job được tạo (`created`) cho tới khi Runner tiếp nhận và khởi động (`started/running`).
  - **Mục đích:** Đánh giá độ khả dụng của cụm Runner. Nếu thời gian chờ $> 30\text{s}$, công cụ ghi nhận cảnh báo Runner pool đang bị nghẽn (thiếu hụt số lượng runner hoặc concurrency đạt mức tối đa).
- `--max_duration 300` (Ngưỡng thời lượng thực thi - 300 giây / 5 phút):
  - Đo lường tổng thời gian chạy thực tế của các Job trong Pipeline.
  - **Mục đích:** Phát hiện các tác vụ bị treo (hanging tasks), build quá lâu do tải thư viện chậm hoặc không tận dụng Docker layer caching, từ đó hỗ trợ đội ngũ tối ưu thời gian phản hồi của CI.

### F4. Tính chất và Cách kích hoạt
- **Chính sách `allow_failure: true`:** Stage này chỉ mang tính chất đo lường và cảnh báo hiệu năng, không chặn đứng luồng phát hành phần mềm nếu xảy ra lỗi.
- **Tuỳ chọn kích hoạt (Optional):** Dự án có nhu cầu giám sát hiệu năng Runner chỉ cần khai báo thêm `- gitlabci-analyser` vào trường `stages:` trong file `.gitlab-ci.yml` của dự án.

---

## 9. SO SÁNH ĐẶC TÍNH KỸ THUẬT GIỮA CÁC STAGES TRONG HỆ THỐNG CI

| Tiêu chí | 1. `detect-secrets` | 2. `build` | 3. `dependency-check` | 4. `upload-bom` | 5. `sonarqube-check` | 6. `gitlabci-analyser` (Tùy chọn) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mục đích chính** | Phát hiện mật khẩu, key, token rò rỉ | Đóng gói mã nguồn & push image Harbor | Quét lỗ hổng SCA & tạo SBOM CycloneDX | Đẩy SBOM lên OWASP Dependency-Track | Phân tích chất lượng & bảo mật mã nguồn tĩnh | Giám sát độ trễ hàng đợi & thời lượng chạy Job |
| **Tag Runner** | `[devsecops]` | `[build]` | `[devsecops]` | `[devsecops]` | `[devsecops]` | `[devsecops]` |
| **Kiểu Container** | Single Container | Multi-container (DinD) | Single Container | Single Container siêu nhẹ | Single Container | Single Container |
| **Image sử dụng** | `.../detect-secrets:v2.8` | `docker:20.10.16` + `docker:dind` | `aquasec/trivy:0.56.1` | `curlimages/curl` | `sonarsource/sonar-scanner-cli:latest` | `.../gitlabci-analyser:v0.2.0` |
| **Quyền thực thi** | Non-privileged | `privileged: true` | Non-privileged | Non-privileged | Non-privileged | Non-privileged |
| **Xử lý thư mục `.git`** | `rm -rf .git/` trước khi quét | Giữ nguyên (versioning) | Giữ nguyên (quét dependency) | Kế thừa artifact | `GIT_DEPTH: 0` (clone đầy đủ) | Giữ nguyên workspace |
| **Đầu vào (Input)** | Toàn bộ mã nguồn commit | Mã nguồn + `Dockerfile` | Thư mục mã nguồn & lock files | File artifact `result1.json` | Toàn bộ mã nguồn & lịch sử Git | Metadata & thời gian thực thi Job/Runner |
| **Đầu ra (Output)** | Log phát hiện secret | Docker Image trên Harbor | File SBOM `result1.json` (Artifact) | HTTP Response từ Dependency-Track API | Báo cáo phân tích chất lượng trên SonarQube | Log hiệu năng và cảnh báo nghẽn Runner |
| **Cấu hình `allow_failure`** | `false` (dừng pipeline) | `false` (dừng pipeline) | `true` (cảnh báo) | `true` (cảnh báo) | `true` (cảnh báo) | `true` (không ảnh hưởng build) |
| **Cơ chế kích hoạt** | Tự động trên mọi nhánh | Tùy nhánh (`dev`/`staging`/`manual prod`) | Tự động sau `build` | Tự động sau `dependency-check` | Tự động sau `upload-bom` | Tùy chọn khi thêm vào `stages:` |

---

## 10. CƠ CHẾ PHẢN HỒI VÀ QUY TRÌNH XỬ LÝ SỰ CỐ TOÀN DIỆN (FEEDBACK LOOP)

Khi một trong các stage gặp sự cố (`Failed` hoặc phát hiện cảnh báo rủi ro), Developer theo dõi trên giao diện GitLab CI/CD và xử lý theo quy trình chuẩn sau:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              QUY TRÌNH PHẢN HỒI VÀ XỬ LÝ SỰ CỐ (FEEDBACK LOOP)                          │
└───────────────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                                    │
        ┌───────────────────────────┬───────────────┴───────────────┬───────────────────────────┐
        ▼                           ▼                               ▼                           ▼
[STAGE DETECT-SECRETS]        [STAGE BUILD]               [STAGE DEPENDENCY-CHECK]      [STAGE UPLOAD-BOM]
        │                           │                               │                           │
        ▼                           ▼                               ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│ Phân loại rủi ro:     │   │ Nguyên nhân:          │   │ Phân tích CVEs:       │   │ Nguyên nhân:          │
│ • Secret thật:        │   │ • Dockerfile sai      │   │ • Nâng cấp version    │   │ • Sai API Key         │
│   - Thu hồi / rotate  │   │ • Sai user/pass Harbor│   │   thư viện trong lock │   │   DEPENDENCY_TRACK_KEY│
│   - Đưa vào CI/CD Vars│   │ • Lỗi build code      │   │ • Nếu chưa có patch:  │   │ • Lỗi kết nối mạng    │
│ • False Positive:     │   │ • Registry đầy bộ nhớ │   │   đánh giá mitigation │   │ • Server bảo trì      │
│   - Thêm EXCLUDE_*    │   │                       │   │                       │   │                       │
└───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘
            │                           │                           │                           │
            └───────────────────────────┴─────────────┬─────────────┴───────────────────────────┘
                                                      │
                                                      ▼
                                      [Developer Commit & Git Push lại]
                                                      │
                                                      ▼
                                  [GitLab tạo Pipeline MỚI chạy lại từ đầu]
```

1. **Trường hợp Stage `detect-secrets` thất bại:**
   - **Nếu là Secret thật bị rò rỉ:** Developer phải lập tức thu hồi/thay thế (rotate) secret bị lộ, xóa hoàn toàn giá trị khỏi mã nguồn, cấu hình lại giá trị thông qua GitLab CI/CD Variables hoặc Secret Management, sau đó commit và push lại.
   - **Nếu là Báo động giả (False Positive):** Khai báo giá trị hoặc đường dẫn thư mục vào biến `EXCLUDE_SECRETS` hoặc `EXCLUDE_FOLDERS` trong file `.gitlab-ci.yml` của dự án, sau đó commit và push lại.

2. **Trường hợp Stage `build` thất bại:**
   - **Nguyên nhân:** Lỗi cú pháp trong `Dockerfile`, thiếu file thư viện nguồn, sai thông tin tài khoản `REGISTRY_PUSH_USER`/`REGISTRY_PUSH_PASSWORD`, hoặc dung lượng Registry đầy.
   - **Khắc phục:** Đọc log chi tiết của job, sửa lỗi mã nguồn hoặc cấu hình build, sau đó commit và push lại.

3. **Trường hợp Stage `dependency-check` phát hiện lỗ hổng:**
   - **Khắc phục:** Kiểm tra bảng kết quả quét trong log job hoặc file artifact. Nâng cấp phiên bản thư viện trong file quản lý dependency (ví dụ: `package.json`, `pom.xml`, `requirements.txt`) lên phiên bản đã được vá lỗi, sau đó commit và push lại.

4. **Trường hợp Stage `upload-bom` gặp sự cố:**
   - **Khắc phục:** Kiểm tra biến `$DEPENDENCY_TRACK_KEY` trong phần *Settings > CI/CD > Variables* của dự án xem đã được cấu hình chính xác quyền ghi hay chưa, kiểm tra trạng thái kết nối tới domain `https://dependency-track.dev.ftech.ai`.

5. **Nguyên tắc vòng lặp (Fresh Pipeline):**
   - Mỗi lần Developer push một commit mới, GitLab sẽ tạo ra một **Pipeline mới hoàn toàn độc lập**. Quy trình sẽ chạy lại từ đầu (từ `detect-secrets` ➔ `build` ➔ `dependency-check` ➔ `upload-bom`), đảm bảo tính toàn vẹn và an toàn tuyệt đối cho hệ thống trước khi chuyển sang các bước GitOps CD tiếp theo.
